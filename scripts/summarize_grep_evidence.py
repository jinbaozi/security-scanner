"""Validate and summarize safe-grep evidence for bounded semantic review."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


SUPPORTED_SCHEMAS = {"1.0"}


def _validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("wrong_input_schema: root must be an object")
    if payload.get("artifact_type") != "safe_grep_result":
        raise ValueError("wrong_input_schema: expected safe_grep_result")
    if payload.get("schema_version") not in SUPPORTED_SCHEMAS:
        raise ValueError("wrong_input_schema: unsupported schema_version")
    samples = payload.get("samples")
    if not isinstance(samples, list):
        raise ValueError("wrong_input_schema: samples must be a list")
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("wrong_input_schema: sample must be an object")
        if not isinstance(sample.get("file"), str) or not sample["file"]:
            raise ValueError("wrong_input_schema: sample.file must be a string")
        if not isinstance(sample.get("line"), int) or isinstance(sample["line"], bool) or sample["line"] < 1:
            raise ValueError("wrong_input_schema: sample.line must be a positive integer")
        if not isinstance(sample.get("match"), str):
            raise ValueError("wrong_input_schema: sample.match must be a string")
    for field in ("matched_files", "matched_lines"):
        if not isinstance(payload.get(field), int) or isinstance(payload[field], bool) or payload[field] < 0:
            raise ValueError(f"wrong_input_schema: {field} must be a non-negative integer")
    return payload


def summarize(payload: dict[str, Any], sample_size: int) -> dict[str, Any]:
    samples = [
        {
            "file": item["file"],
            "line": item["line"],
            "match": item["match"][:240],
        }
        for item in payload["samples"][:sample_size]
    ]
    return {
        "artifact_type": "grep_evidence_summary",
        "schema_version": "1.0",
        "source_artifact_type": payload["artifact_type"],
        "source_schema_version": payload["schema_version"],
        "matched_files": payload["matched_files"],
        "candidate_count": payload["matched_lines"],
        "sample_count": len(samples),
        "samples": samples,
        "source_truncated": bool(payload.get("truncated", False)),
        "summary_truncated": len(payload["samples"]) > len(samples),
        "requires_review": payload["matched_lines"] > 0,
        "semantic_verdict": "not_assessed",
    }


def _bounded_payload(summary: dict[str, Any], max_bytes: int) -> str:
    while True:
        encoded = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) <= max_bytes:
            return encoded
        if not summary["samples"]:
            raise ValueError("max_bytes_too_small")
        summary["samples"].pop()
        summary["sample_count"] = len(summary["samples"])
        summary["summary_truncated"] = True


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Create a bounded safe-grep evidence summary.",
        status_name="grep-evidence-summary",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=16384)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print("grep-evidence-summary status=blocked reason=input_not_found", file=sys.stderr)
        return 5
    try:
        source = json.loads(args.input.read_text(encoding="utf-8"))
        payload = _validate(source)
        summary = summarize(payload, max(0, args.sample_size))
        encoded = _bounded_payload(summary, max(512, args.max_bytes))
        _atomic_write(args.output, encoded)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        reason = "wrong_input_schema" if isinstance(exc, ValueError) and str(exc).startswith("wrong_input_schema") else type(exc).__name__
        print(f"grep-evidence-summary status=failed reason={reason}", file=sys.stderr)
        return 4

    print(
        f"grep-evidence-summary status=ok candidates={summary['candidate_count']} "
        f"samples={summary['sample_count']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
