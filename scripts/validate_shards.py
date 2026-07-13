"""Validate reconnaissance shard sizes without loading file lists into Pi."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_SHARD_FILES = 50
WARN_SHARD_FILES = 40
MAX_TOTAL_SHARDS = 16


def validate_shards(scan_plan: dict[str, Any]) -> dict[str, Any]:
    shards = scan_plan.get("source_shards", [])
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    counts: list[int] = []

    if not isinstance(shards, list):
        errors.append({"reason": "source_shards_not_array"})
        shards = []

    for index, shard in enumerate(shards):
        if not isinstance(shard, dict):
            errors.append({"shard": index, "reason": "shard_not_object"})
            continue
        count = shard.get("file_count")
        if not isinstance(count, int):
            files = shard.get("files")
            count = len(files) if isinstance(files, list) else -1
        shard_id = shard.get("id", index)
        if count < 0:
            errors.append({"shard": shard_id, "reason": "missing_file_count"})
            continue
        counts.append(count)
        if count > MAX_SHARD_FILES:
            errors.append(
                {
                    "shard": shard_id,
                    "file_count": count,
                    "reason": "shard_file_limit_exceeded",
                    "limit": MAX_SHARD_FILES,
                }
            )
        elif count > WARN_SHARD_FILES:
            warnings.append(
                {
                    "shard": shard_id,
                    "file_count": count,
                    "reason": "shard_near_file_limit",
                    "limit": MAX_SHARD_FILES,
                }
            )

    if len(shards) > MAX_TOTAL_SHARDS:
        errors.append(
            {
                "reason": "total_shard_limit_exceeded",
                "shard_count": len(shards),
                "limit": MAX_TOTAL_SHARDS,
            }
        )

    status = "fail" if errors else ("warn" if warnings else "pass")
    return {
        "status": status,
        "shard_count": len(shards),
        "max_shard_files": max(counts, default=0),
        "limits": {
            "max_shard_files": MAX_SHARD_FILES,
            "warn_shard_files": WARN_SHARD_FILES,
            "max_total_shards": MAX_TOTAL_SHARDS,
        },
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Scan Plan source shards.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print("shard-validation status=blocked reason=input_not_found")
        return 5
    try:
        scan_plan = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("shard-validation status=failed reason=invalid_json")
        return 4

    report = validate_shards(scan_plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"shard-validation status={report['status']} "
        f"shards={report['shard_count']} max_files={report['max_shard_files']} "
        f"errors={len(report['errors'])} warnings={len(report['warnings'])} "
        f"output={args.output}"
    )
    return {"pass": 0, "warn": 2, "fail": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
