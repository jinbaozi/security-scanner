#!/usr/bin/env python3
"""Build a complete, deterministic values object for report templates."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cli_contract import CompactArgumentParser  # noqa: E402
from scripts.render_template import collect_placeholders, parse_contract  # noqa: E402


DIMENSION_PREFIX = {
    "elf": "ELF",
    "url": "URL",
    "secret": "SECRET",
    "comment": "COMMENT",
    "fileleak": "FILELEAK",
    "permission": "PERMISSION",
    "crypto": "CRYPTO",
    "network": "NETWORK",
    "component-info": "COMPONENT_INFO",
    "dependency": "DEPENDENCY",
    "secure-coding": "SECURE_CODING",
    "integrity": "INTEGRITY",
    "content-compliance": "CONTENT_COMPLIANCE",
}
COUNT_SUFFIXES = (
    "_COUNT", "_TOTAL", "_CONFIRMED", "_SUSPECTED", "_NEEDS_HUMAN",
    "_UNVERIFIED", "_REJECTED",
)


def read_json(path: Path | None, default: Any) -> Any:
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _dimension_status(value: Any) -> str:
    return str(value.get("status", "unverified") if isinstance(value, dict) else value).lower()


def _display_dimension_status(value: Any) -> str:
    status = _dimension_status(value)
    return {
        "ready": "已执行",
        "pass": "已执行",
        "blocked": "已阻断",
        "failed": "失败",
        "degraded": "降级",
        "partial": "部分完成",
        "unverified": "未验证",
        "missing": "缺失",
        "skipped": "已跳过",
        "not_applicable": "无适用输入",
    }.get(status, f"未知状态（{status}）")


def default_value(name: str) -> Any:
    if name.endswith(COUNT_SUFFIXES) or name in {"TOTAL_FILES", "SCAN_FILES", "TOTAL_FINDINGS"}:
        return 0
    if name.startswith("SECTION_"):
        return "- 无可用扫描结论；请检查维度覆盖状态。"
    if name.startswith("TABLE_"):
        return "| 项目 | 状态 |\n|---|---|\n| 当前扫描 | 未验证 |"
    if name.endswith("_AUDIT"):
        return "UNVERIFIED"
    if name in {"FAILED_AGENTS", "RETRIED_AGENTS", "DEGRADED_DIMENSIONS", "REJECTED_FINDINGS", "NEEDS_HUMAN_FINDINGS", "UNVERIFIED_FINDINGS", "EXCLUDED_FILES"}:
        return 0
    return "未提供"


def build_values(
    template: str,
    component_name: str,
    target_path: str,
    scan_date: str,
    scan_plan: dict[str, Any],
    findings: list[dict[str, Any]],
    base: dict[str, Any],
    dimension_statuses: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = {name: default_value(name) for name in collect_placeholders(template)}
    values.update(base)
    dimension_statuses = dimension_statuses or {}
    normalized_statuses = {
        dimension: _dimension_status(dimension_statuses.get(dimension, "missing"))
        for dimension in DIMENSION_PREFIX
    }
    blocked_states = {"blocked", "failed"}
    degraded_states = {"degraded", "partial", "unverified", "missing"}
    finding_states = {str(item.get("status", "WARN")).upper() for item in findings}
    if any(state in blocked_states for state in normalized_statuses.values()):
        report_status = "BLOCKED"
    elif "FAIL" in finding_states:
        report_status = "FAIL"
    elif not dimension_statuses or any(state in degraded_states for state in normalized_statuses.values()):
        report_status = "UNVERIFIED"
    elif "WARN" in finding_states or any(state not in {"PASS", "WARN", "FAIL"} for state in finding_states):
        report_status = "WARN"
    else:
        report_status = "PASS"
    values.update(
        {
            "COMPONENT_NAME": component_name,
            "TARGET_PATH": target_path,
            "SCAN_DATE": scan_date,
            "TOTAL_FILES": scan_plan.get("total_files", 0),
            "SCAN_FILES": scan_plan.get("scan_files", 0),
            "TOTAL_FINDINGS": len(findings),
            "REPORT_STATUS": report_status,
        }
    )
    severity = Counter(str(item.get("severity", "info")).lower() for item in findings)
    for level in ("critical", "high", "medium", "low", "info"):
        values[f"{level.upper()}_COUNT"] = severity[level]

    by_dimension: dict[str, list[dict[str, Any]]] = {key: [] for key in DIMENSION_PREFIX}
    for finding in findings:
        dimension = str(finding.get("dimension", ""))
        if dimension in by_dimension:
            by_dimension[dimension].append(finding)
    for dimension, prefix in DIMENSION_PREFIX.items():
        items = by_dimension[dimension]
        verdicts = Counter(str(item.get("verdict", "unverified")).lower() for item in items)
        values[f"{prefix}_TOTAL"] = len(items)
        for verdict in ("confirmed", "suspected", "needs_human", "unverified", "rejected"):
            values[f"{prefix}_{verdict.upper()}"] = verdicts[verdict]
        section_name = f"SECTION_{prefix}_FINDINGS"
        if section_name in values and items:
            values[section_name] = "\n".join(
                f"- `{item.get('id', 'UNKNOWN')}`：{item.get('detail', '见结构化 findings。')}"
                for item in items[:200]
            )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Build complete report template values.",
        status_name="report-values",
    )
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--component-name", required=True)
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--scan-date", required=True)
    parser.add_argument("--scan-plan", type=Path)
    parser.add_argument("--findings", type=Path)
    parser.add_argument("--base-values", type=Path)
    parser.add_argument("--dimension-statuses", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        template = args.template.read_text(encoding="utf-8")
        scan_plan = read_json(args.scan_plan, {})
        findings_data = read_json(args.findings, [])
        base = read_json(args.base_values, {})
        dimension_statuses = read_json(args.dimension_statuses, {})
        if isinstance(findings_data, dict):
            findings_data = findings_data.get("findings", [])
        if not isinstance(scan_plan, dict) or not isinstance(findings_data, list) or not isinstance(base, dict) or not isinstance(dimension_statuses, dict):
            raise ValueError("input JSON shape is invalid")
        values = build_values(
            template, args.component_name, args.target_path, args.scan_date,
            scan_plan, findings_data, base, dimension_statuses,
        )
        manifest_path = args.template.parent / "report-manifest.yaml"
        if manifest_path.is_file() and "SECTION_DIMENSION_INDEX" in values:
            import yaml

            dimensions = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))["dimensions"]
            date_slug = args.scan_date.replace("-", "")
            values["SECTION_DIMENSION_INDEX"] = "\n".join(
                f"- {entry['display_name']}：`{entry['output'].replace('{component_name}', args.component_name).replace('{date}', date_slug)}`"
                for entry in dimensions.values()
            )
            values["SECTION_DIMENSION_STATUS"] = "\n".join(
                f"- {entry['display_name']}：{_display_dimension_status(dimension_statuses.get(dimension, 'unverified'))}"
                for dimension, entry in dimensions.items()
            )
        missing = [name for name in parse_contract(template)["required"] if name not in values or values[name] is None or (isinstance(values[name], str) and not values[name].strip())]
        if missing:
            raise ValueError("required values remain incomplete")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"report-values status=failed reason={type(exc).__name__}", file=sys.stderr)
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(values, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"report-values status=pass fields={len(values)} missing=0 output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
