#!/usr/bin/env python3
"""Resolve a persisted file-list artifact declared by a normalized Scan Plan."""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _blocked(reason: str) -> int:
    print(f"artifact-resolver status=blocked reason={reason}", file=sys.stderr)
    return 5


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Resolve a Scan Plan file-list artifact.",
        status_name="artifact-resolver",
    )
    parser.add_argument("--scan-plan", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--file-class", required=True)
    parser.add_argument("--base-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    scan_plan = args.scan_plan.expanduser().resolve()
    report_root = args.report_root.expanduser().resolve()
    if not scan_plan.is_file():
        return _blocked("scan_plan_not_found")
    try:
        plan = json.loads(scan_plan.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("artifact-resolver status=failed reason=invalid_scan_plan", file=sys.stderr)
        return 4

    file_lists = plan.get("file_lists")
    entry = file_lists.get(args.file_class) if isinstance(file_lists, dict) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        return _blocked("file_list_not_declared")

    declared = Path(entry["path"]).expanduser()
    list_path = (declared if declared.is_absolute() else report_root / declared).resolve()
    if not list_path.is_relative_to(report_root):
        return _blocked("file_list_outside_report_root")
    try:
        mode = list_path.stat().st_mode
    except OSError:
        return _blocked("file_list_not_found")
    if not stat.S_ISREG(mode) or list_path.is_symlink():
        return _blocked("file_list_not_regular")

    try:
        entries = [
            line.strip()
            for line in list_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError:
        return _blocked("file_list_unreadable")
    actual_count = len(entries)
    declared_count = entry.get("count")
    if not isinstance(declared_count, int) or declared_count != actual_count:
        print("artifact-resolver status=failed reason=file_list_count_mismatch", file=sys.stderr)
        return 4

    payload = {
        "artifact_type": "resolved_file_list",
        "schema_version": "1.0",
        "status": "ready",
        "file_class": args.file_class,
        "scan_plan": str(scan_plan),
        "report_root": str(report_root),
        "list_path": str(list_path),
        "declared_count": declared_count,
        "actual_count": actual_count,
    }
    if args.file_class == "elf":
        base_root = args.base_root.expanduser().resolve() if args.base_root else None
        invalid_count = 0
        for value in entries:
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                if base_root is None:
                    invalid_count += 1
                    continue
                candidate = base_root / candidate
            try:
                with candidate.resolve().open("rb") as stream:
                    if stream.read(4) != bytes([0x7F]) + b"ELF":
                        invalid_count += 1
            except OSError:
                invalid_count += 1
        payload["magic_verified"] = invalid_count == 0
        payload["invalid_count"] = invalid_count
        if invalid_count:
            payload["status"] = "blocked"
            _atomic_write(args.output, payload)
            print(
                "artifact-resolver status=blocked "
                "reason=elf_classification_mismatch "
                f"invalid={invalid_count} output={args.output}",
                file=sys.stderr,
            )
            return 5
    _atomic_write(args.output, payload)
    print(
        f"artifact-resolver status=ready class={args.file_class} "
        f"files={actual_count} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
