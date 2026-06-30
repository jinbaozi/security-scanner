#!/usr/bin/env python3
"""按 scanner 维度生成 redline 条款切片。"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


AUTOMATED_MODES = {"full", "partial"}
DEFAULT_DIM_ORDER = (
    "elf",
    "url",
    "secret",
    "comment",
    "fileleak",
    "permission",
    "network",
    "crypto",
    "component-info",
    "dependency",
    "secure-coding",
    "integrity",
    "content-compliance",
)
FENCED_YAML_RE = re.compile(r"```ya?ml\s*\n(?P<body>.*?)\n```", re.DOTALL | re.IGNORECASE)
SPEC_SECTION_RE = re.compile(
    r"^###\s+(?P<clause_id>\d+(?:\.\d+)+)\s*$"
    r"(?P<body>.*?)(?=^###\s+\d+(?:\.\d+)+\s*$|\Z)",
    re.DOTALL | re.MULTILINE,
)


def load_mapping(mapping_path: Path) -> list[dict[str, Any]]:
    """Load the self-contained YAML mapping embedded in redline-mapping.md."""
    text = mapping_path.read_text(encoding="utf-8")
    match = FENCED_YAML_RE.search(text)
    if not match:
        raise ValueError(f"未在 {mapping_path} 中找到 fenced YAML mapping")

    data = yaml.safe_load(match.group("body"))
    if not isinstance(data, dict):
        raise ValueError(f"{mapping_path} 的 YAML 顶层必须是 mapping")

    mapping = data.get("redline_mapping")
    if not isinstance(mapping, list):
        raise ValueError(f"{mapping_path} 缺少 redline_mapping 列表")

    for index, item in enumerate(mapping, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"redline_mapping 第 {index} 项必须是 mapping")
    return mapping


def load_spec_summaries(spec_path: Path) -> dict[str, str]:
    """Extract the normative text as a compact summary for each clause."""
    if not spec_path.is_file():
        return {}

    text = spec_path.read_text(encoding="utf-8")
    summaries: dict[str, str] = {}
    for match in SPEC_SECTION_RE.finditer(text):
        body = match.group("body")
        summary_match = re.search(
            r"\*\*规范正文：\*\*\s*(?P<summary>.*?)(?=\n\*\*解读列表：\*\*)",
            body,
            re.DOTALL,
        )
        if not summary_match:
            continue
        summary = " ".join(summary_match.group("summary").split())
        if summary:
            summaries[match.group("clause_id")] = summary
    return summaries


def grouped_by_dim(
    mapping: list[dict[str, Any]],
    summaries: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in mapping:
        automation = item.get("automation")
        scanner_dims = item.get("scanner_dims") or []
        if automation not in AUTOMATED_MODES:
            if scanner_dims:
                raise ValueError(f"manual/非自动条款不应声明 scanner_dims: {item.get('clause_id')}")
            continue
        if not scanner_dims:
            continue

        clause_id = str(item.get("clause_id", "")).strip()
        if not clause_id:
            raise ValueError("存在缺少 clause_id 的 mapping 项")

        rendered = {
            "clause_id": clause_id,
            "rl_ids": item.get("rl_ids") or [],
            "automation": automation,
            "profile_min": item.get("profile_min"),
            "summary": summaries.get(clause_id, f"redline clause {clause_id}"),
        }
        for optional_key in ("manual_note", "terminology_pending"):
            if optional_key in item:
                rendered[optional_key] = item[optional_key]

        for dim in scanner_dims:
            grouped[str(dim)].append(rendered)
    return grouped


def yaml_inline_list(values: list[Any]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def append_block_scalar(lines: list[str], key: str, value: str) -> None:
    lines.append(f"    {key}: >-")
    scalar_lines = str(value).splitlines() or [""]
    lines.extend(f"      {line}" for line in scalar_lines)


def render_dim_slice(dim: str, clauses: list[dict[str, Any]]) -> str:
    lines = [
        f"# redline 条款切片：{dim}",
        "",
        "> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。",
        "> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。",
        "",
        "```yaml",
        "redline_clauses:",
    ]
    for clause in clauses:
        lines.extend(
            [
                f"  - clause_id: {clause['clause_id']}",
                f"    rl_ids: {yaml_inline_list(clause['rl_ids'])}",
                f"    automation: {clause['automation']}",
                f"    profile_min: {clause['profile_min']}",
            ]
        )
        append_block_scalar(lines, "summary", clause["summary"])
        if "manual_note" in clause:
            append_block_scalar(lines, "manual_note", clause["manual_note"])
        if clause.get("terminology_pending") is True:
            lines.append("    terminology_pending: true")
    lines.extend(["```", ""])
    return "\n".join(lines)


def dim_sort_key(dim: str) -> tuple[int, str]:
    try:
        return (DEFAULT_DIM_ORDER.index(dim), dim)
    except ValueError:
        return (len(DEFAULT_DIM_ORDER), dim)


def write_slices(grouped: dict[str, list[dict[str, Any]]], scanners_dir: Path) -> list[Path]:
    written: list[Path] = []
    for dim in sorted(grouped, key=dim_sort_key):
        output_path = scanners_dir / dim / "references" / "redline-clauses.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_dim_slice(dim, grouped[dim]), encoding="utf-8")
        written.append(output_path)
    return written


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="按 scanner 维度生成 redline 条款切片。")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=repo_root / "references" / "redline-mapping.md",
        help="输入 redline-mapping.md，默认 references/redline-mapping.md。",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=repo_root / "references" / "redline-spec.md",
        help="输入 redline-spec.md，用于提取 summary。",
    )
    parser.add_argument(
        "--scanners-dir",
        type=Path,
        default=repo_root / "scanners",
        help="输出 scanners 目录，默认 scanners/。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping = load_mapping(args.mapping)
    summaries = load_spec_summaries(args.spec)
    grouped = grouped_by_dim(mapping, summaries)
    written = write_slices(grouped, args.scanners_dir)
    print(f"已生成 {len(written)} 个 redline 条款切片")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
