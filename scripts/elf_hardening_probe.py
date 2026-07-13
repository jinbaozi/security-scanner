"""Deterministic ELF hardening probe for the ELF scanner.

The prompt-driven scanner consumes this helper's JSON instead of constructing
checksec commands directly. This keeps invocation failures distinct from a
confirmed tool-unavailable fallback.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


Runner = Callable[..., "CommandResult"]
UNKNOWN = "unknown/unverified"


@dataclass
class CommandResult:
    command: list[str] | tuple[str, ...]
    returncode: int
    stdout: str | bytes = ""
    stderr: str | bytes = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def default_runner(command: list[str], cwd: Path | None = None, **kwargs: Any) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)


def _text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _summary(value: str | bytes, limit: int = 300) -> str:
    text = " ".join(_text(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _looks_like_missing_tool(result: CommandResult) -> bool:
    combined = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
    runtime_dependency_signal = (
        "error while loading shared libraries" in combined
        or "bad interpreter" in combined
        or "cannot execute" in combined
        or "permission denied" in combined
        or (".so" in combined and "not found" in combined)
    )
    if runtime_dependency_signal:
        return False
    return result.returncode == 127 or "command not found" in combined or "not found" in combined


def _looks_like_runtime_broken(result: CommandResult) -> bool:
    combined = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
    signals = (
        "permission denied",
        "error while loading shared libraries",
        "cannot execute",
        "bad interpreter",
        "no such file or directory",
        "missing dependency",
    )
    return result.returncode == 126 or any(signal in combined for signal in signals) or (
        ".so" in combined and "not found" in combined
    )


def _looks_like_executable_help(result: CommandResult) -> bool:
    combined = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
    return result.ok or "usage" in combined or "checksec" in combined


def _classify_checksec_failure(result: CommandResult) -> str:
    combined = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
    if _looks_like_missing_tool(result):
        return "missing"
    if _looks_like_runtime_broken(result):
        return "broken"
    if "usage" in combined or "unknown option" in combined or "unrecognized option" in combined:
        return "invocation_error"
    return "invocation_error"


def _result_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    statuses = ("ready", "degraded", "blocked", "unverified", "skipped")
    return {
        status: sum(1 for entry in results if entry.get("status") == status)
        for status in statuses
    }


def _update_coverage(result: dict[str, Any], input_total: int) -> None:
    results = [entry for entry in result.get("results", []) if isinstance(entry, dict)]
    result["input_total"] = input_total
    result["result_total"] = len(results)
    result["result_counts"] = _result_counts(results)
    result["coverage_complete"] = len(results) == input_total


def _status_line(result: dict[str, Any]) -> str:
    counts = _result_counts(
        [entry for entry in result.get("results", []) if isinstance(entry, dict)]
    )
    return (
        "elf_probe "
        f"status={result.get('status')} "
        f"files={len(result.get('results', []))} "
        f"checksec={result.get('checksec_state')} "
        f"mode={result.get('selected_mode') or 'none'} "
        f"ready={counts['ready']} degraded={counts['degraded']} "
        f"blocked={counts['blocked']} unverified={counts['unverified']} "
        f"skipped={counts['skipped']}"
    )


def _is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


class ElfHardeningProbe:
    def __init__(self, runner: Runner = default_runner) -> None:
        self.runner = runner
        self.tool_invocations: list[dict[str, Any]] = []

    def probe(self, files: list[str | Path]) -> dict[str, Any]:
        self.tool_invocations = []
        results: list[dict[str, Any] | None] = []
        readable: list[tuple[int, Path]] = []

        for file_path in files:
            path = Path(file_path)
            if not path.is_file() or not os.access(path, os.R_OK):
                results.append(
                    {
                        "file": str(path),
                        "status": "unverified",
                        "source": None,
                        "mode": None,
                        "parser": None,
                        "checks": {},
                        "failure_reason": "file_unreadable",
                        "tool_invocation_refs": [],
                    }
                )
                continue
            if not _is_elf(path):
                results.append(
                    {
                        "file": str(path),
                        "status": "skipped",
                        "source": None,
                        "mode": None,
                        "parser": None,
                        "checks": {},
                        "failure_reason": "not_elf",
                        "tool_invocation_refs": [],
                    }
                )
                continue
            results.append(None)
            readable.append((len(results) - 1, path))

        checksec_state = "not_run"
        selected_mode: str | None = None
        fallback_used = False
        fallback_reason: str | None = None
        unavailable_proof: dict[str, Any] | None = None

        if readable:
            availability = self._check_checksec_available()
            if availability["available"]:
                checksec_state = "available"
                for index, path in readable:
                    entry = self._probe_with_checksec(path)
                    if entry["status"] == "blocked" and entry.get("failure_reason") in {"missing", "broken"}:
                        fallback_used = True
                        fallback_reason = "checksec_confirmed_unavailable"
                        if selected_mode is None:
                            selected_mode = "readelf"
                        results[index] = self._probe_with_readelf(path, unavailable_proof=entry.get("unavailable_proof"))
                        continue
                    results[index] = entry
                    if entry["status"] == "ready" and selected_mode is None:
                        selected_mode = entry["mode"]
            else:
                checksec_state = "confirmed_unavailable"
                fallback_used = True
                fallback_reason = "checksec_confirmed_unavailable"
                unavailable_proof = availability["proof"]
                selected_mode = "readelf"
                for index, path in readable:
                    results[index] = self._probe_with_readelf(path, unavailable_proof=unavailable_proof)

        final_results = [entry for entry in results if entry is not None]
        status = self._overall_status(final_results, fallback_used)
        payload = {
            "status": status,
            "checksec_state": checksec_state,
            "selected_mode": selected_mode,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "unavailable_proof": unavailable_proof,
            "tool_invocations": self.tool_invocations,
            "results": final_results,
        }
        _update_coverage(payload, len(files))
        return payload

    def _overall_status(self, results: list[dict[str, Any]], fallback_used: bool) -> str:
        statuses = {entry.get("status") for entry in results}
        if "blocked" in statuses or "skipped" in statuses:
            return "blocked"
        if fallback_used:
            return "degraded"
        if "unverified" in statuses:
            return "blocked"
        if "degraded" in statuses:
            return "degraded"
        return "ready"

    def _run(self, command: list[str]) -> tuple[CommandResult, int]:
        try:
            result = self.runner(command)
        except FileNotFoundError as exc:
            result = CommandResult(command, 127, "", str(exc))
        except OSError as exc:
            result = CommandResult(command, 126, "", str(exc))

        index = len(self.tool_invocations)
        self.tool_invocations.append(
            {
                "command": list(command),
                "exit_code": result.returncode,
                "stderr_summary": _summary(result.stderr),
                "parser": None,
                "classification": None,
            }
        )
        return result, index

    def _mark_invocation(
        self,
        index: int,
        *,
        parser: str | None = None,
        classification: str | None = None,
    ) -> None:
        invocation = self.tool_invocations[index]
        if parser is not None:
            invocation["parser"] = parser
        if classification is not None:
            invocation["classification"] = classification

    def _check_checksec_available(self) -> dict[str, Any]:
        result, index = self._run(["checksec", "--help"])
        if _looks_like_missing_tool(result):
            self._mark_invocation(index, classification="missing")
            return {"available": False, "proof": self._unavailable_proof("missing", result, index)}
        if _looks_like_runtime_broken(result) and not _looks_like_executable_help(result):
            self._mark_invocation(index, classification="broken")
            return {"available": False, "proof": self._unavailable_proof("broken", result, index)}
        if _looks_like_executable_help(result):
            self._mark_invocation(index, classification="available")
            return {"available": True, "proof": None}

        self._mark_invocation(index, classification="broken")
        return {"available": False, "proof": self._unavailable_proof("broken", result, index)}

    def _unavailable_proof(self, classification: str, result: CommandResult, index: int) -> dict[str, Any]:
        return {
            "tool": "checksec",
            "classification": classification,
            "command": list(result.command),
            "exit_code": result.returncode,
            "stderr_summary": _summary(result.stderr),
            "audit_log_ref": f"tool_invocations[{index}]",
        }

    def _probe_with_checksec(self, path: Path) -> dict[str, Any]:
        json_modes = (
            ("format_json", ["checksec", f"--file={path}", "--format=json"]),
            ("output_json", ["checksec", f"--file={path}", "--output=json"]),
        )
        refs: list[int] = []
        parse_error_seen = False
        last_failure = "invocation_error"
        unavailable_failure: tuple[str, CommandResult, int] | None = None

        for mode, command in json_modes:
            result, index = self._run(command)
            refs.append(index)
            if result.ok:
                try:
                    payload = json.loads(_text(result.stdout))
                except json.JSONDecodeError:
                    parse_error_seen = True
                    last_failure = "parse_error"
                    self._mark_invocation(index, parser="json", classification="parse_error")
                    continue
                self._mark_invocation(index, parser="json", classification="ok")
                return self._checksec_entry(path, mode, "json", self._normalize_json_checks(path, payload), refs)

            classification = _classify_checksec_failure(result)
            if classification in {"missing", "broken"} and not parse_error_seen:
                unavailable_failure = (classification, result, index)
            else:
                last_failure = classification if classification in {"invocation_error", "parse_error"} else "invocation_error"
            self._mark_invocation(index, parser="json", classification=classification)

        text_command = ["checksec", f"--file={path}"]
        result, index = self._run(text_command)
        refs.append(index)
        if result.ok:
            checks = self._parse_checksec_text(_text(result.stdout))
            if checks:
                self._mark_invocation(index, parser="text", classification="ok")
                return self._checksec_entry(path, "text", "text", checks, refs)
            self._mark_invocation(index, parser="text", classification="parse_error")
            return self._blocked_entry(path, "parse_error", refs)

        classification = _classify_checksec_failure(result)
        self._mark_invocation(index, parser="text", classification=classification)
        if classification in {"missing", "broken"} and not parse_error_seen:
            unavailable_failure = (classification, result, index)
            return self._blocked_entry(
                path,
                classification,
                refs,
                unavailable_proof=self._unavailable_proof(classification, result, index),
            )
        if unavailable_failure is not None and not parse_error_seen:
            classification, failed_result, failed_index = unavailable_failure
            return self._blocked_entry(
                path,
                classification,
                refs,
                unavailable_proof=self._unavailable_proof(classification, failed_result, failed_index),
            )
        else:
            last_failure = classification if classification in {"invocation_error", "parse_error"} else "invocation_error"
        return self._blocked_entry(path, last_failure, refs)

    def _checksec_entry(
        self,
        path: Path,
        mode: str,
        parser: str,
        checks: dict[str, Any],
        refs: list[int],
    ) -> dict[str, Any]:
        return {
            "file": str(path),
            "status": "ready",
            "source": "checksec",
            "mode": mode,
            "parser": parser,
            "checks": checks,
            "failure_reason": None,
            "tool_invocation_refs": [f"tool_invocations[{index}]" for index in refs],
        }

    def _blocked_entry(
        self,
        path: Path,
        reason: str,
        refs: list[int],
        *,
        unavailable_proof: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "file": str(path),
            "status": "blocked",
            "source": "checksec",
            "mode": None,
            "parser": None,
            "checks": {},
            "failure_reason": reason,
            "unavailable_proof": unavailable_proof,
            "tool_invocation_refs": [f"tool_invocations[{index}]" for index in refs],
        }

    def _normalize_json_checks(self, path: Path, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            path_keys = (str(path), path.name)
            for key in path_keys:
                item = payload.get(key)
                if isinstance(item, dict):
                    return item
            return payload
        if isinstance(payload, list):
            return {"items": payload}
        return {"value": payload}

    def _parse_checksec_text(self, output: str) -> dict[str, str]:
        if "RELRO" not in output or "NX" not in output:
            return {}

        checks: dict[str, str] = {}
        phrase_map = {
            "relro": ("Full RELRO", "Partial RELRO", "No RELRO"),
            "stack_canary": ("Canary found", "No canary found", "No canary"),
            "nx": ("NX enabled", "NX disabled"),
            "pie": ("PIE enabled", "No PIE", "DSO"),
            "rpath": ("No RPATH", "RPATH"),
            "runpath": ("No RUNPATH", "RUNPATH"),
            "symbols": ("No Symbols", "Symbols"),
        }
        for check, phrases in phrase_map.items():
            for phrase in phrases:
                if phrase in output:
                    checks[check] = phrase
                    break

        if "FORTIFY" in output:
            checks["fortify_source"] = "Yes" if " Yes " in f" {output} " else "unknown"
        return checks

    def _probe_with_readelf(
        self,
        path: Path,
        *,
        unavailable_proof: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        commands = {
            "program_headers": ["readelf", "-l", str(path)],
            "dynamic": ["readelf", "-d", str(path)],
            "elf_header": ["readelf", "-h", str(path)],
            "symbols": ["readelf", "-s", str(path)],
            "file": ["file", str(path)],
        }
        outputs: dict[str, dict[str, Any]] = {}
        refs: list[int] = []
        evidence_count = 0
        for key, command in commands.items():
            result, index = self._run(command)
            refs.append(index)
            classification = "ok" if result.ok else _classify_checksec_failure(result)
            self._mark_invocation(index, parser="readelf" if command[0] == "readelf" else "file", classification=classification)
            output = _text(result.stdout)
            has_output = result.ok and bool(output.strip())
            if has_output:
                evidence_count += 1
            outputs[key] = {"ok": result.ok, "output": output, "has_output": has_output}

        if evidence_count == 0:
            return {
                "file": str(path),
                "status": "unverified",
                "source": "readelf",
                "mode": "readelf",
                "parser": "readelf",
                "checks": {},
                "failure_reason": "fallback_tools_unavailable",
                "unavailable_proof": unavailable_proof,
                "tool_invocation_refs": [f"tool_invocations[{index}]" for index in refs],
            }

        return {
            "file": str(path),
            "status": "degraded",
            "source": "readelf",
            "mode": "readelf",
            "parser": "readelf",
            "checks": self._derive_readelf_checks(outputs),
            "failure_reason": "checksec_confirmed_unavailable",
            "unavailable_proof": unavailable_proof,
            "tool_invocation_refs": [f"tool_invocations[{index}]" for index in refs],
        }

    def _derive_readelf_checks(self, outputs: dict[str, dict[str, Any]]) -> dict[str, str]:
        def output_for(key: str) -> str:
            evidence = outputs.get(key, {})
            if evidence.get("has_output"):
                return str(evidence.get("output", ""))
            return ""

        program_headers = output_for("program_headers")
        dynamic = output_for("dynamic")
        elf_header = output_for("elf_header")
        symbols = output_for("symbols")
        file_output = output_for("file")
        checks: dict[str, str] = {
            "nx": UNKNOWN,
            "relro": UNKNOWN,
            "bind_now": UNKNOWN,
            "pie": UNKNOWN,
            "stack_canary": UNKNOWN,
            "rpath_runpath": UNKNOWN,
            "fortify_source": UNKNOWN,
            "strip": UNKNOWN,
        }

        if "GNU_STACK" in program_headers:
            checks["nx"] = "NX disabled" if "RWE" in program_headers else "NX enabled"

        if program_headers:
            has_relro = "GNU_RELRO" in program_headers
            has_bind_now = "BIND_NOW" in dynamic
            if has_relro and dynamic:
                checks["relro"] = "Full RELRO" if has_bind_now else "Partial RELRO"
            elif not has_relro:
                checks["relro"] = "No RELRO"
        if dynamic:
            checks["bind_now"] = "BIND_NOW" if "BIND_NOW" in dynamic else "No BIND_NOW"

        if "DYN" in elf_header:
            checks["pie"] = "PIE enabled"
        elif "EXEC" in elf_header:
            checks["pie"] = "No PIE"

        if symbols:
            checks["stack_canary"] = "Canary found" if "__stack_chk_fail" in symbols else "No canary"
            checks["fortify_source"] = "Fortified" if "_chk@" in symbols else "Not fortified"
        if dynamic:
            checks["rpath_runpath"] = "RPATH/RUNPATH set" if (
                "RPATH" in dynamic or "RUNPATH" in dynamic
            ) else "No RPATH/RUNPATH"
        if "not stripped" in file_output:
            checks["strip"] = "Not stripped"
        elif "stripped" in file_output:
            checks["strip"] = "Stripped"
        return checks


def _read_list_file(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _shift_tool_refs(value: Any, offset: int) -> Any:
    """Shift tool_invocations[N] references when merging probe batches."""
    if isinstance(value, dict):
        return {key: _shift_tool_refs(item, offset) for key, item in value.items()}
    if isinstance(value, list):
        return [_shift_tool_refs(item, offset) for item in value]
    if isinstance(value, str) and value.startswith("tool_invocations[") and value.endswith("]"):
        try:
            index = int(value[len("tool_invocations[") : -1])
        except ValueError:
            return value
        return f"tool_invocations[{index + offset}]"
    return value


def _write_probe_checkpoint(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main(argv: list[str] | None = None, *, runner: Runner = default_runner) -> int:
    parser = CompactArgumentParser(
        description="Probe ELF hardening evidence with checksec/readelf.",
        status_name="elf_probe",
    )
    parser.add_argument("--file", dest="files", action="append", default=[], help="ELF file path. May be repeated.")
    parser.add_argument("--list-file", type=Path, help="Text file containing one ELF path per line.")
    parser.add_argument("--output-json", type=Path, required=True, help="Path for the full probe JSON artifact.")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--checkpoint", action="store_true", help="Atomically save after every batch.")
    parser.add_argument("--resume", action="store_true", help="Skip files already present in output JSON.")
    args = parser.parse_args(argv)

    files = list(dict.fromkeys(args.files))
    if args.list_file:
        if not args.list_file.is_file():
            print("elf_probe status=blocked reason=list_file_not_found", file=sys.stderr)
            return 5
        try:
            files.extend(path for path in _read_list_file(args.list_file) if path not in files)
        except OSError:
            print("elf_probe status=blocked reason=list_file_unreadable", file=sys.stderr)
            return 5
    if not files:
        parser.error("at least one --file or --list-file entry is required")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    result: dict[str, Any] = {
        "status": "ready",
        "checksec_state": "not_run",
        "selected_mode": None,
        "fallback_used": False,
        "fallback_reason": None,
        "unavailable_proof": None,
        "tool_invocations": [],
        "results": [],
    }
    previous_batches = 0
    if args.resume and args.output_json.is_file():
        try:
            loaded = json.loads(args.output_json.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                result.update(loaded)
                previous_batches = int(result.get("checkpoint", {}).get("batches_completed", 0))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            print("elf_probe status=blocked reason=invalid_resume_checkpoint")
            return 5

    completed = {
        str(entry.get("file"))
        for entry in result.get("results", [])
        if isinstance(entry, dict) and entry.get("file")
    }
    pending = [path for path in files if str(Path(path)) not in completed]
    resumed_count = len(files) - len(pending)
    batch_statuses = [result.get("status", "ready")] if completed else []
    batches_completed = previous_batches

    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        batch_result = ElfHardeningProbe(runner=runner).probe(
            [Path(file) for file in batch]
        )
        offset = len(result.get("tool_invocations", []))
        shifted = _shift_tool_refs(batch_result, offset)
        result.setdefault("tool_invocations", []).extend(shifted["tool_invocations"])
        result.setdefault("results", []).extend(shifted["results"])
        batch_statuses.append(shifted["status"])
        if result.get("checksec_state") == "not_run":
            result["checksec_state"] = shifted["checksec_state"]
        if result.get("selected_mode") is None:
            result["selected_mode"] = shifted["selected_mode"]
        result["fallback_used"] = bool(result.get("fallback_used") or shifted["fallback_used"])
        result["fallback_reason"] = result.get("fallback_reason") or shifted["fallback_reason"]
        result["unavailable_proof"] = result.get("unavailable_proof") or shifted["unavailable_proof"]
        result["status"] = (
            "blocked"
            if "blocked" in batch_statuses
            else ("degraded" if "degraded" in batch_statuses else "ready")
        )
        batches_completed += 1
        processed = min(start + len(batch), len(pending))
        result["checkpoint"] = {
            "input_total": len(files),
            "resumed_count": resumed_count,
            "batches_completed": batches_completed,
            "batch_size": args.batch_size,
            "remaining": len(pending) - processed,
        }
        _update_coverage(result, len(files))
        if args.checkpoint:
            _write_probe_checkpoint(args.output_json, result)

    result["checkpoint"] = {
        "input_total": len(files),
        "resumed_count": resumed_count,
        "batches_completed": batches_completed,
        "batch_size": args.batch_size,
        "remaining": 0,
    }
    _update_coverage(result, len(files))
    _write_probe_checkpoint(args.output_json, result)
    print(_status_line(result))
    return 0 if result["status"] == "ready" else (3 if result["status"] == "degraded" else 5)


if __name__ == "__main__":
    raise SystemExit(main())
