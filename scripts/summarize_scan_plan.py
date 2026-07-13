"""Create a bounded, Pi-safe summary of a potentially large Scan Plan."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path, PurePath
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, dict):
        count = value.get("count")
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            return count
    return 0


def _file_list(scan_plan: dict[str, Any], name: str, legacy_key: str) -> Any:
    file_lists = scan_plan.get("file_lists")
    if isinstance(file_lists, dict) and name in file_lists:
        return file_lists[name]
    return scan_plan.get(legacy_key, [])


def _validate_scan_plan(scan_plan: dict[str, Any]) -> None:
    """Reject phase -0 materialization payloads and malformed Scan Plans."""
    scan_markers = {"file_lists", "source_shards", "all_files", "elf_files"}
    materialization_markers = {"input_kind", "source_roots", "binary_roots"}
    if materialization_markers.intersection(scan_plan) and not scan_markers.intersection(scan_plan):
        raise ValueError("wrong_input_schema: expected Scan Plan, got materialization")
    if not isinstance(scan_plan.get("component_name"), str) or not scan_plan["component_name"].strip():
        raise ValueError("wrong_input_schema: component_name is required")
    if not isinstance(scan_plan.get("source_shards", []), list):
        raise ValueError("wrong_input_schema: source_shards must be a list")
    file_lists = scan_plan.get("file_lists")
    if file_lists is not None and not isinstance(file_lists, dict):
        raise ValueError("wrong_input_schema: file_lists must be an object")


def _short_path(item: Any) -> str | None:
    raw = item.get("path") if isinstance(item, dict) else item
    if not isinstance(raw, str) or not raw:
        return None
    parts = PurePath(raw).parts
    return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def _samples(items: Any, limit: int) -> list[str]:
    if isinstance(items, dict):
        items = items.get("samples", [])
    if not isinstance(items, list):
        return []
    result: list[str] = []
    for item in items:
        path = _short_path(item)
        if path and path not in result:
            result.append(path)
        if len(result) >= limit:
            break
    return result


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    index = max(0, math.ceil(len(sorted_values) * percentile) - 1)
    return sorted_values[index]


def summarize(scan_plan: dict[str, Any], sample_size: int) -> dict[str, Any]:
    shards = scan_plan.get("source_shards", [])
    shard_sizes: list[int] = []
    if isinstance(shards, list):
        for shard in shards:
            if not isinstance(shard, dict):
                continue
            count = shard.get("file_count")
            if not isinstance(count, int):
                count = _count(shard.get("files"))
            shard_sizes.append(count)
    shard_sizes.sort()

    materialization = scan_plan.get("materialization", {})
    if not isinstance(materialization, dict):
        materialization = {}

    warnings: list[str] = []
    if shard_sizes and shard_sizes[-1] > 50:
        warnings.append(
            f"shard size {shard_sizes[-1]} exceeds absolute limit 50"
        )
    if len(shard_sizes) > 16:
        warnings.append(f"shard count {len(shard_sizes)} exceeds limit 16")

    all_files = _file_list(scan_plan, "all", "all_files")
    elf_files = _file_list(scan_plan, "elf", "elf_files")
    config_files = _file_list(scan_plan, "config", "config_files")
    dependency_files = _file_list(scan_plan, "dependency", "dependency_files")
    excluded_files = _file_list(scan_plan, "excluded", "excluded")
    source_items: list[Any] = []
    if isinstance(shards, list):
        for shard in shards:
            if not isinstance(shard, dict):
                continue
            shard_samples = shard.get("samples")
            if isinstance(shard_samples, list):
                source_items.extend(shard_samples[:sample_size])
            elif isinstance(shard.get("files"), list):
                source_items.extend(shard["files"][:sample_size])
            if len(source_items) >= sample_size:
                break

    samples = {
        "elf": _samples(elf_files, sample_size),
        "source": _samples(source_items or all_files, sample_size),
        "config": _samples(config_files, sample_size),
        "excluded": _samples(excluded_files, sample_size),
    }
    represented_samples = sum(len(value) for value in samples.values())

    return {
        "version": "1.1",
        "artifact_type": "scan_plan_summary",
        "component_name": scan_plan.get("component_name"),
        "total_files": _count(scan_plan.get("total_files")),
        "scan_files": _count(scan_plan.get("scan_files")),
        "all_files_count": _count(all_files),
        "elf_count": _count(elf_files),
        "config_count": _count(config_files),
        "dependency_count": _count(dependency_files),
        "excluded_count": _count(excluded_files),
        "source_shards_count": len(shard_sizes),
        "shard_size_distribution": {
            "min": min(shard_sizes, default=0),
            "max": max(shard_sizes, default=0),
            "median": _percentile(shard_sizes, 0.5),
            "p95": _percentile(shard_sizes, 0.95),
        },
        "materialization": {
            "input_kind": materialization.get("input_kind"),
            "status": materialization.get("status"),
            "source_roots_count": _count(materialization.get("source_roots")),
            "binary_roots_count": _count(materialization.get("binary_roots")),
            "error_count": _count(materialization.get("errors")),
        },
        "samples": samples,
        "warnings": warnings,
        "truncated": _count(all_files) > represented_samples or any(
            size > sample_size for size in shard_sizes
        ),
    }


def _bounded_payload(summary: dict[str, Any], max_bytes: int) -> str:
    while True:
        payload = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) <= max_bytes:
            return payload
        largest_key = max(
            summary["samples"], key=lambda key: len(summary["samples"][key])
        )
        if summary["samples"][largest_key]:
            summary["samples"][largest_key].pop()
            summary["truncated"] = True
            continue
        raise ValueError("max-bytes is too small for Scan Plan summary")


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Summarize a large Scan Plan.",
        status_name="scan-plan-summary",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--max-bytes", type=int, default=65536)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print("scan-plan-summary status=blocked reason=input_not_found", file=sys.stderr)
        return 5
    try:
        scan_plan = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(scan_plan, dict):
            raise ValueError("wrong_input_schema: Scan Plan must be an object")
        _validate_scan_plan(scan_plan)
        summary = summarize(scan_plan, max(0, args.sample_size))
        payload = _bounded_payload(summary, max(512, args.max_bytes))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        reason = (
            "wrong_input_schema"
            if isinstance(exc, ValueError) and str(exc).startswith("wrong_input_schema")
            else type(exc).__name__
        )
        print(f"scan-plan-summary status=failed reason={reason}", file=sys.stderr)
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(args.output)
    print(
        f"scan-plan-summary status=ok files={summary['total_files']} "
        f"shards={summary['source_shards_count']} bytes={len(payload.encode('utf-8'))} "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
