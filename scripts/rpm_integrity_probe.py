"""Deterministic, locale-stable RPM signature and digest probe."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


Runner = Callable[..., "CommandResult"]


@dataclass
class CommandResult:
    command: list[str] | tuple[str, ...]
    returncode: int
    stdout: str | bytes = ""
    stderr: str | bytes = ""


def _text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _summary(value: str | bytes, limit: int = 500) -> str:
    text = " ".join(_text(value).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def default_runner(command: list[str], **kwargs: Any) -> CommandResult:
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "LANG": "C"})
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=kwargs.get("timeout", 120),
            env=env,
        )
        return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError as exc:
        return CommandResult(command, 127, "", str(exc))
    except PermissionError as exc:
        return CommandResult(command, 126, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command, 124, exc.stdout or "", exc.stderr or "timed out")
    except OSError as exc:
        return CommandResult(command, 126, "", str(exc))


def classify_rpm_check(result: CommandResult) -> str:
    combined = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
    if result.returncode == 127 or "command not found" in combined:
        return "tool_missing"
    if result.returncode == 126 or "permission denied" in combined or "error while loading shared libraries" in combined:
        return "tool_broken"
    if result.returncode == 124:
        return "tool_timeout"
    if "nokey" in combined or "public key not available" in combined or "missing key" in combined:
        return "missing_key"
    if "not trusted" in combined or "nottrusted" in combined:
        return "untrusted_key"
    if any(signal in combined for signal in ("digests signatures not ok", "digests signatures not correct", "signature: bad", "bad signature", "signatures not ok", "signatures not correct")):
        return "bad_signature"
    if any(signal in combined for signal in ("digests not ok", "digests not correct", "digest: bad", "bad digest")):
        return "bad_digest"
    if "not signed" in combined or "unsigned" in combined:
        return "unsigned"
    signature_signals = ("rsa/sha", "dsa/sha", "pgp", "gpg", "signature, key id")
    if result.returncode == 0 and any(signal in combined for signal in signature_signals):
        return "verified"
    if result.returncode == 0 and ("digests ok" in combined or "digest: ok" in combined):
        return "unsigned"
    if result.returncode != 0:
        return "unknown_failure"
    return "parse_error"


def _execution_status(verification_status: str) -> str:
    if verification_status in {"verified", "unsigned", "bad_digest", "bad_signature"}:
        return "ready"
    if verification_status in {"missing_key", "untrusted_key", "tool_missing", "tool_broken"}:
        return "unverified"
    return "blocked"


def probe_rpms(paths: list[Path], runner: Runner = default_runner) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    invocations: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file() or not os.access(path, os.R_OK):
            results.append(
                {
                    "file": str(path),
                    "status": "unverified",
                    "verification_status": "file_unreadable",
                    "tool_invocation_ref": None,
                }
            )
            continue
        command = ["rpm", "--checksig", str(path)]
        result = runner(command, timeout=120)
        classification = classify_rpm_check(result)
        invocation_index = len(invocations)
        invocations.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "locale": "C",
                "parser": "rpm_checksig_text_v1",
                "classification": classification,
                "stdout_summary": _summary(result.stdout),
                "stderr_summary": _summary(result.stderr),
            }
        )
        results.append(
            {
                "file": str(path),
                "status": _execution_status(classification),
                "verification_status": classification,
                "tool_invocation_ref": f"tool_invocations[{invocation_index}]",
            }
        )

    counts = {
        state: sum(1 for entry in results if entry["status"] == state)
        for state in ("ready", "unverified", "blocked")
    }
    if counts["blocked"]:
        status = "blocked"
    elif counts["unverified"]:
        status = "degraded"
    else:
        status = "ready"
    return {
        "version": "1.0",
        "artifact_type": "rpm_integrity_probe",
        "status": status,
        "input_total": len(paths),
        "result_total": len(results),
        "coverage_complete": len(results) == len(paths),
        "result_counts": counts,
        "tool_invocations": invocations,
        "results": results,
    }


def _read_list(path: Path) -> list[Path]:
    return [
        Path(line.strip())
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None, *, runner: Runner = default_runner) -> int:
    parser = CompactArgumentParser(
        description="Probe RPM signature and digest status.",
        status_name="rpm-integrity-probe",
    )
    parser.add_argument("--rpm", dest="rpms", action="append", type=Path, default=[])
    parser.add_argument("--list-file", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    paths = list(args.rpms)
    if args.list_file:
        if not args.list_file.is_file():
            print("rpm-integrity-probe status=blocked reason=list_file_not_found")
            return 5
        paths.extend(_read_list(args.list_file))
    paths = list(dict.fromkeys(paths))
    if not paths:
        parser.error("at least one --rpm or --list-file entry is required")

    payload = probe_rpms(paths, runner=runner)
    _atomic_write(args.output_json, payload)
    counts = payload["result_counts"]
    print(
        f"rpm-integrity-probe status={payload['status']} files={payload['result_total']} "
        f"ready={counts['ready']} unverified={counts['unverified']} blocked={counts['blocked']}"
    )
    return 5 if payload["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
