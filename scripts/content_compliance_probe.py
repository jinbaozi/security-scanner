#!/usr/bin/env python3
"""Run local content-compliance rules without placing rule text in model calls."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


def load_rules(path: Path) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    category = "content_compliance"
    seen: set[tuple[str, str]] = set()
    regex_fence = False

    def append_rule(value: str, target: str, *, literal: bool) -> None:
        key = (target, value)
        if not value or key in seen:
            return
        seen.add(key)
        expression = re.escape(value) if literal else value
        rules.append(
            {
                "rule_id": f"CC-{len(rules) + 1:03d}",
                "category": category,
                "target": target,
                "regex": re.compile(expression, re.IGNORECASE),
            }
        )

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped == "```regex":
            regex_fence = True
            continue
        if regex_fence and stripped == "```":
            regex_fence = False
            continue
        if regex_fence:
            append_rule(stripped, "path", literal=False)
            continue
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        if not line.lstrip().startswith("|"):
            continue
        for value in re.findall(r"`([^`]+)`", line):
            append_rule(value, "content", literal=True)
    if not rules:
        raise ValueError("rules file contains no patterns")
    return rules


def listed_paths(files_file: Path, base_root: Path) -> tuple[list[Path], int, int]:
    paths: list[Path] = []
    missing = outside = 0
    seen: set[Path] = set()
    for raw in files_file.read_text(encoding="utf-8", errors="replace").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value).expanduser()
        candidate = (candidate if candidate.is_absolute() else base_root / candidate).resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.is_relative_to(base_root):
            outside += 1
        elif not candidate.is_file() or candidate.is_symlink():
            missing += 1
        else:
            paths.append(candidate)
    return paths, missing, outside


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Run local content-compliance rules.", status_name="content-probe"
    )
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--files-file", type=Path, required=True)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--max-results", type=int, default=200)
    args = parser.parse_args(argv)

    rules_path = args.rules.expanduser().resolve()
    files_file = args.files_file.expanduser().resolve()
    base_root = args.base_root.expanduser().resolve()
    if not rules_path.is_file() or not files_file.is_file() or not base_root.is_dir():
        print("content-probe status=blocked reason=input_not_found", file=sys.stderr)
        return 5
    try:
        rules = load_rules(rules_path)
        paths, missing, outside = listed_paths(files_file, base_root)
    except (OSError, ValueError, re.error) as exc:
        print(f"content-probe status=failed reason={type(exc).__name__}", file=sys.stderr)
        return 4

    compact: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    max_results = max(0, args.max_results)
    for path in paths:
        relative = str(path.relative_to(base_root))
        path_is_sensitive = False
        for rule in rules:
            if rule["target"] != "path" or rule["regex"].search(relative) is None:
                continue
            path_is_sensitive = True
            raw.append(
                {
                    "rule_id": rule["rule_id"],
                    "category": rule["category"],
                    "file": relative,
                    "line": None,
                    "evidence": relative,
                }
            )
            if len(compact) < max_results:
                compact.append(
                    {
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "file": "<redacted-path>",
                        "line": None,
                    }
                )
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            missing += 1
            continue
        for line_number, line in enumerate(lines, 1):
            for rule in rules:
                if rule["target"] != "content":
                    continue
                match = rule["regex"].search(line)
                if match is None:
                    continue
                raw.append(
                    {
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "file": relative,
                        "line": line_number,
                        "evidence": line[:500],
                    }
                )
                if len(compact) < max_results:
                    compact.append(
                        {
                            "rule_id": rule["rule_id"],
                            "category": rule["category"],
                            "file": "<redacted-path>" if path_is_sensitive else relative,
                            "line": line_number,
                        }
                    )

    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_text = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in raw)
    args.evidence_output.write_text(evidence_text, encoding="utf-8")
    os.chmod(args.evidence_output, 0o600)
    report = {
        "status": "pass",
        "ruleset": rules_path.name,
        "rule_count": len(rules),
        "scanned_files": len(paths),
        "missing_files": missing,
        "outside_root_files": outside,
        "original_count": len(raw),
        "emitted_count": len(compact),
        "truncated_count": max(0, len(raw) - len(compact)),
        "matches": compact,
        "evidence_ref": str(args.evidence_output),
    }
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"content-probe status=pass files={len(paths)} matches={len(raw)} "
        f"emitted={len(compact)} output={args.output_summary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
