#!/usr/bin/env python3
"""Deterministically split Scan Plan source shard lists at 50 files."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


MAX_FILES = 50


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Normalize Scan Plan shard sizes.", status_name="shard-normalize"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-root", type=Path)
    args = parser.parse_args(argv)
    report_root = (args.report_root or args.input.resolve().parent.parent).resolve()
    try:
        plan = json.loads(args.input.read_text(encoding="utf-8"))
        shards = plan.get("source_shards", [])
        if not isinstance(shards, list):
            raise ValueError("source_shards must be an array")
        normalized: list[dict[str, Any]] = []
        split_count = 0
        for index, shard in enumerate(shards):
            if not isinstance(shard, dict):
                raise ValueError("shard must be an object")
            file_list = shard.get("file_list")
            if file_list:
                list_path = Path(file_list)
                list_path = list_path if list_path.is_absolute() else report_root / list_path
                files = [line.strip() for line in list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            elif isinstance(shard.get("files"), list):
                files = [str(item) for item in shard["files"]]
                list_path = report_root / "recon" / "shards" / f"source-{index:03d}.txt"
            else:
                raise ValueError("shard has no file_list or files")
            chunks = [files[start:start + MAX_FILES] for start in range(0, len(files), MAX_FILES)] or [[]]
            split_count += max(0, len(chunks) - 1)
            for part, chunk in enumerate(chunks):
                target = list_path if len(chunks) == 1 else list_path.with_name(f"{list_path.stem}.part-{part:03d}{list_path.suffix or '.txt'}")
                atomic_write(target, "".join(f"{item}\n" for item in chunk))
                item = {key: value for key, value in shard.items() if key not in {"files", "file_count", "file_list", "samples", "origin_counts"}}
                item["id"] = shard.get("id", index) if len(chunks) == 1 else f"{shard.get('id', index)}-{part:03d}"
                item["file_list"] = str(target.relative_to(report_root))
                item["file_count"] = len(chunk)
                item["samples"] = chunk[:3]
                origin_counts = shard.get("origin_counts")
                if isinstance(origin_counts, dict) and len(origin_counts) == 1:
                    item["origin_counts"] = {next(iter(origin_counts)): len(chunk)}
                normalized.append(item)
        plan["source_shards"] = normalized
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"shard-normalize status=failed reason={type(exc).__name__}", file=sys.stderr)
        return 4

    atomic_write(args.output, json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    print(f"shard-normalize status=pass shards={len(normalized)} splits={split_count} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
