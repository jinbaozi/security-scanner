#!/usr/bin/env python3
"""Build complete, deterministic values objects for report templates."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cli_contract import CompactArgumentParser  # noqa: E402
from scripts.render_template import collect_placeholders, parse_contract  # noqa: E402
from scripts.runtime_paths import SkillRootWriteForbidden, require_outside_skill_root  # noqa: E402


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
FINDING_REQUIRED_FIELDS = {
    "id", "dimension", "file", "line", "check_item", "status", "severity",
    "confidence", "verdict", "verdict_reasoning", "detail", "suggestion",
    "evidence", "redline_clause", "rl_ids",
}
READY_STATES = {"ready", "pass"}
BLOCKED_STATES = {"blocked", "failed"}
DEGRADED_STATES = {"degraded", "partial", "unverified", "missing"}
SKIPPED_STATES = {"skipped", "not_applicable"}


def read_json(path: Path | None, default: Any) -> Any:
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _dimension_status(value: Any) -> str:
    return str(value.get("status", "unverified") if isinstance(value, dict) else value).lower()


def _dimension_reason(value: Any) -> str:
    if not isinstance(value, dict):
        return "-"
    return str(value.get("reason") or value.get("note") or "-")


def _display_dimension_status(value: Any) -> str:
    status = _dimension_status(value)
    return {
        "ready": "已执行", "pass": "已执行", "blocked": "已阻断", "failed": "失败",
        "degraded": "降级", "partial": "部分完成", "unverified": "未验证",
        "missing": "缺失", "skipped": "已跳过", "not_applicable": "无适用输入",
    }.get(status, f"未知状态（{status}）")


def _nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _scan_count(scan_plan: dict[str, Any], name: str) -> int:
    entry = (scan_plan.get("file_lists") or {}).get(name, {})
    return _nonnegative_int(entry.get("count")) if isinstance(entry, dict) else 0


def _source_count(scan_plan: dict[str, Any]) -> int:
    shards = scan_plan.get("source_shards") or []
    if not isinstance(shards, list):
        return 0
    return sum(
        _nonnegative_int(shard.get("file_count"))
        for shard in shards if isinstance(shard, dict)
    )


def _markdown_cell(value: Any, limit: int | None = None) -> str:
    text = str(value if value not in (None, "") else "-")
    text = text.replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "\\`")
    return text[:limit] if limit is not None else text


def default_value(name: str) -> Any:
    if name.endswith(COUNT_SUFFIXES) or name in {
        "TOTAL_FILES", "SCAN_FILES", "TOTAL_FINDINGS", "ELF_COUNT", "SOURCE_COUNT",
        "CONFIG_COUNT", "EXCLUDED_FILES",
    }:
        return 0
    if name.startswith("SECTION_"):
        return "- 无可用扫描结论；请检查维度覆盖状态。"
    if name.startswith("TABLE_"):
        return "| 项目 | 状态 |\n|---|---|\n| 当前扫描 | 未验证 |"
    if name.endswith("_AUDIT"):
        return "UNVERIFIED"
    if name in {
        "FAILED_AGENTS", "RETRIED_AGENTS", "DEGRADED_DIMENSIONS", "REJECTED_FINDINGS",
        "NEEDS_HUMAN_FINDINGS", "UNVERIFIED_FINDINGS",
    }:
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
    normalized = {
        dimension: _dimension_status(dimension_statuses.get(dimension, "missing"))
        for dimension in DIMENSION_PREFIX
    }
    finding_states = {str(item.get("status", "WARN")).upper() for item in findings}
    if any(state in BLOCKED_STATES for state in normalized.values()):
        report_status = "BLOCKED"
    elif "FAIL" in finding_states:
        report_status = "FAIL"
    elif not dimension_statuses or any(state in DEGRADED_STATES for state in normalized.values()):
        report_status = "UNVERIFIED"
    elif "WARN" in finding_states or any(state not in {"PASS", "WARN", "FAIL"} for state in finding_states):
        report_status = "WARN"
    else:
        report_status = "PASS"

    values.update({
        "COMPONENT_NAME": component_name,
        "TARGET_PATH": target_path,
        "SCAN_DATE": scan_date,
        "TOTAL_FILES": _nonnegative_int(scan_plan.get("total_files")),
        "SCAN_FILES": _nonnegative_int(scan_plan.get("scan_files")),
        "TOTAL_FINDINGS": len(findings),
        "REPORT_STATUS": report_status,
        "ELF_COUNT": _scan_count(scan_plan, "elf"),
        "SOURCE_COUNT": _source_count(scan_plan),
        "CONFIG_COUNT": _scan_count(scan_plan, "config"),
        "EXCLUDED_FILES": _scan_count(scan_plan, "excluded"),
    })
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
            rows = [
                f"- `{_markdown_cell(item.get('id', 'UNKNOWN'))}`：{_markdown_cell(item.get('detail') or '见结构化 findings。', 120)}"
                for item in items[:50]
            ]
            if len(items) > 50:
                rows.append(f"- ... 本维度已裁截，完整 {len(items)} 条见独立详细报告及 findings JSON。")
            values[section_name] = "\n".join(rows)
    return values


def _load_manifest(template_path: Path) -> dict[str, Any]:
    path = template_path.parent / "report-manifest.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid report manifest")
    return data


def _resolve_dimension(template_path: Path, manifest: dict[str, Any]) -> tuple[str, str] | None:
    for key, entry in (manifest.get("dimensions") or {}).items():
        if isinstance(entry, dict) and entry.get("template") == template_path.name:
            return str(key), str(entry.get("display_name") or key)
    return None


def _finding_audit(items: list[dict[str, Any]], dim_key: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    ids: set[str] = set()
    allowed_values = {
        "status": {"PASS", "WARN", "FAIL"},
        "severity": {"critical", "high", "medium", "low", "info"},
        "confidence": {"high", "medium", "low"},
        "verdict": {"confirmed", "suspected", "rejected", "needs_human", "unverified"},
    }
    for index, item in enumerate(items):
        missing = sorted(FINDING_REQUIRED_FIELDS - set(item))
        if missing:
            issues.append(f"finding[{index}] 缺少字段：{','.join(missing)}")
        finding_id = str(item.get("id", ""))
        if not finding_id:
            issues.append(f"finding[{index}] ID 为空")
        elif finding_id in ids:
            issues.append(f"finding ID 重复：{finding_id}")
        ids.add(finding_id)
        if str(item.get("dimension", "")) != dim_key:
            issues.append(f"finding {finding_id or index} 维度不匹配")
        for field, allowed in allowed_values.items():
            if item.get(field) not in allowed:
                issues.append(f"finding {finding_id or index} 的 {field} 非法")
        if not isinstance(item.get("rl_ids"), list):
            issues.append(f"finding {finding_id or index} 的 rl_ids 非数组")
    return ("PASS" if not issues else "WARN"), issues


def _dimension_detail(items: list[dict[str, Any]], status_value: Any) -> str:
    status = _dimension_status(status_value)
    if not items:
        if status in READY_STATES:
            return "未发现问题。该维度已执行；配置、代码或输入变化后应重新扫描。"
        return f"该维度未完成可信检查：状态为{_display_dimension_status(status_value)}，原因：{_dimension_reason(status_value)}。"

    header = (
        "| ID | 文件 | 行号 | 严重度 | 裁决 | 检查项 | 问题描述 | 修复建议 |\n"
        "|----|------|------|--------|------|--------|----------|----------|"
    )
    rows: list[str] = []
    used_bytes = 0
    for item in items[:200]:
        row = (
            f"| `{_markdown_cell(item.get('id', 'UNKNOWN'))}` | {_markdown_cell(item.get('file'))} | "
            f"{_markdown_cell(item.get('line'))} | {_markdown_cell(item.get('severity'))} | "
            f"{_markdown_cell(item.get('verdict'))} | {_markdown_cell(item.get('check_item'))} | "
            f"{_markdown_cell(item.get('detail'), 80)} | {_markdown_cell(item.get('suggestion'), 80)} |"
        )
        row_bytes = len((row + "\n").encode("utf-8"))
        if used_bytes + row_bytes > 30000:
            break
        rows.append(row)
        used_bytes += row_bytes
    if len(rows) < len(items):
        rows.append(
            f"| ... | 已裁截 | 30 KiB/200 条上限 | - | - | - | "
            f"本维度共 {len(items)} 条，仅列示前 {len(rows)} 条，完整列表见 findings JSON | - |"
        )
    return header + "\n" + "\n".join(rows)


def _dimension_audit(dim_key: str, items: list[dict[str, Any]], status_value: Any) -> str:
    field_status, issues = _finding_audit(items, dim_key)
    counts = Counter(str(item.get("status", "")).upper() for item in items)
    known_count = sum(counts[name] for name in ("FAIL", "WARN", "PASS"))
    consistency = "PASS" if known_count == len(items) else "WARN"
    status = _dimension_status(status_value)
    coverage = "PASS" if status in READY_STATES else _display_dimension_status(status_value)
    notes = f"；问题：{'；'.join(issues[:3])}" if issues else ""
    return (
        f"字段完整性：{field_status}；数据一致性：{consistency}；"
        f"覆盖完整性：{coverage}（维度 {dim_key}，状态 {_display_dimension_status(status_value)}，"
        f"命中 {len(items)} 条 finding，原因：{_dimension_reason(status_value)}）{notes}。"
    )


def _display_list(values: Any, field: str = "path") -> str:
    if not isinstance(values, list) or not values:
        return "无记录"
    rendered: list[str] = []
    for value in values:
        item = value.get(field) if isinstance(value, dict) else value
        rendered.append(_markdown_cell(item))
    return "<br>".join(rendered)


def _materialization_section(materialization: dict[str, Any]) -> str:
    errors = materialization.get("errors") if isinstance(materialization.get("errors"), list) else []
    patches = materialization.get("applied_patches") if isinstance(materialization.get("applied_patches"), list) else []
    return "\n".join([
        "| 项目 | 值 |", "|------|-----|",
        f"| 输入类型 | {_markdown_cell(materialization.get('input_kind') or '未验证')} |",
        f"| 物化状态 | {_markdown_cell(materialization.get('status') or 'unverified')} |",
        f"| 源根 | {_display_list(materialization.get('source_roots'))} |",
        f"| 二进制根 | {_display_list(materialization.get('binary_roots'))} |",
        f"| SRPM spec | {_display_list(materialization.get('srpm_spec_files'), field='path')} |",
        f"| 已应用 Patch | {len(patches)} 个：{_display_list(patches)} |",
        f"| builddep 状态 | {_markdown_cell(materialization.get('builddep_status') or '未验证')} |",
        f"| 发现错误 | {len(errors)} 个：{_display_list(errors)} |",
    ])


def _load_redline_mapping() -> list[dict[str, Any]]:
    path = ROOT / "references" / "redline-mapping.md"
    text = path.read_text(encoding="utf-8")
    start = text.find("redline_mapping:")
    if start < 0:
        raise ValueError("redline mapping not found")
    yaml_text = text[start:]
    fence = yaml_text.find("\n```")
    if fence >= 0:
        yaml_text = yaml_text[:fence]
    data = yaml.safe_load(yaml_text)
    mapping = data.get("redline_mapping") if isinstance(data, dict) else None
    if not isinstance(mapping, list) or len(mapping) != 40:
        raise ValueError("redline mapping must contain 40 clauses")
    clause_ids = [str(item.get("clause_id", "")) for item in mapping if isinstance(item, dict)]
    if len(clause_ids) != 40 or len(set(clause_ids)) != 40 or any(not item for item in clause_ids):
        raise ValueError("redline clause ids must be unique")
    return mapping


def _redline_tables(
    mapping: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    statuses: dict[str, Any],
    materialization: dict[str, Any],
) -> tuple[str, str]:
    coverage_rows: list[str] = []
    manual_rows: list[str] = []
    materialization_blocked = str(materialization.get("status", "")).lower() in BLOCKED_STATES
    for clause in mapping:
        clause_id = str(clause["clause_id"])
        automation = str(clause.get("automation", "manual"))
        dimensions = [str(item) for item in clause.get("scanner_dims") or []]
        allowed_rl_ids = {str(item) for item in clause.get("rl_ids") or []}
        matches: list[dict[str, Any]] = []
        invalid_bindings: list[str] = []
        for finding in findings:
            if str(finding.get("redline_clause") or "") != clause_id:
                continue
            finding_rl_ids = {str(item) for item in finding.get("rl_ids") or []}
            finding_dimension = str(finding.get("dimension", ""))
            if (
                finding_dimension not in dimensions or not finding_rl_ids or
                not finding_rl_ids.issubset(allowed_rl_ids)
            ):
                invalid_bindings.append(str(finding.get("id", "UNKNOWN")))
                continue
            if str(finding.get("verdict", "")).lower() in {"confirmed", "suspected"}:
                matches.append(finding)

        dim_states = [_dimension_status(statuses.get(dim, "missing")) for dim in dimensions]
        if automation == "manual":
            coverage = "manual"
            explanation = clause.get("manual_note") or "待人工复核"
        elif invalid_bindings:
            coverage = "degraded"
            explanation = f"非法条款/RL 绑定：{','.join(invalid_bindings)}"
        elif materialization_blocked:
            coverage = "degraded"
            explanation = "输入物化失败，自动覆盖结论不可信"
        elif any(state in SKIPPED_STATES for state in dim_states):
            coverage = "skipped_by_profile" if any(state == "skipped" for state in dim_states) else "not applicable"
            explanation = "相关维度未调度或无适用输入"
        elif any(state in BLOCKED_STATES | DEGRADED_STATES for state in dim_states):
            coverage = "degraded"
            explanation = "相关维度未完整执行"
        elif matches:
            coverage = "covered"
            explanation = "finding: " + ",".join(str(item.get("id", "UNKNOWN")) for item in matches)
        elif dimensions and all(state in READY_STATES for state in dim_states):
            coverage = "no finding"
            explanation = "自动检查已执行，未发现问题"
        else:
            coverage = "degraded"
            explanation = "缺少可信执行状态"
        note = str(clause.get("manual_note") or "")
        if automation == "partial" and note:
            explanation = f"{explanation}；人工复核：{note}"
        coverage_rows.append(
            f"| {_markdown_cell(clause_id)} | {_markdown_cell(automation)} | "
            f"{_markdown_cell(clause.get('profile_min'))} | {_markdown_cell(','.join(dimensions) or '人工')} | "
            f"{coverage} | {_markdown_cell(explanation, 180)} |"
        )
        if automation == "manual":
            manual_rows.append(
                f"| {_markdown_cell(clause_id)} | {_markdown_cell(clause.get('manual_note') or '待人工复核', 120)} | "
                "供应链 / 项目负责人 | 待人工复核 |"
            )
    return "\n".join(coverage_rows), "\n".join(manual_rows)


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(description="Build complete report template values.", status_name="report-values")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--component-name", required=True)
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--scan-date", required=True)
    parser.add_argument("--scan-plan", type=Path)
    parser.add_argument("--findings", type=Path)
    parser.add_argument("--base-values", type=Path)
    parser.add_argument("--dimension-statuses", type=Path)
    parser.add_argument("--materialization", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        args.output = require_outside_skill_root(args.output, ROOT)
    except SkillRootWriteForbidden:
        print("report-values status=blocked reason=skill_root_write_forbidden", file=sys.stderr)
        return 5
    try:
        template = args.template.read_text(encoding="utf-8")
        scan_plan = read_json(args.scan_plan, {})
        findings_data = read_json(args.findings, [])
        base = read_json(args.base_values, {})
        dimension_statuses = read_json(args.dimension_statuses, {})
        materialization = read_json(args.materialization, scan_plan.get("materialization", {}) if isinstance(scan_plan, dict) else {})
        if isinstance(findings_data, dict):
            findings_data = findings_data.get("findings", [])
        if not all((
            isinstance(scan_plan, dict), isinstance(findings_data, list), isinstance(base, dict),
            isinstance(dimension_statuses, dict), isinstance(materialization, dict),
        )) or any(not isinstance(item, dict) for item in findings_data):
            raise ValueError("input JSON shape is invalid")

        manifest = _load_manifest(args.template)
        resolved_dimension = _resolve_dimension(args.template, manifest)
        if resolved_dimension:
            dim_key, display_name = resolved_dimension
            base = dict(base)
            base.setdefault("DIM_KEY", dim_key)
            base.setdefault("DISPLAY_NAME", display_name)
        values = build_values(
            template, args.component_name, args.target_path, args.scan_date,
            scan_plan, findings_data, base, dimension_statuses,
        )

        dimensions = manifest.get("dimensions") or {}
        if "SECTION_DIMENSION_INDEX" in values:
            values["SECTION_DIMENSION_INDEX"] = "\n".join(
                f"- {entry['display_name']}：`{entry['output'].replace('{component_name}', args.component_name).replace('{date}', args.scan_date)}`"
                for entry in dimensions.values()
            )
        if "SECTION_DIMENSION_STATUS" in values:
            values["SECTION_DIMENSION_STATUS"] = "\n".join(
                f"- {entry['display_name']}：{_display_dimension_status(dimension_statuses.get(dimension, 'unverified'))}"
                for dimension, entry in dimensions.items()
            )

        dim_key = str(base.get("DIM_KEY", ""))
        if dim_key:
            items = [item for item in findings_data if str(item.get("dimension", "")) == dim_key]
            counts = Counter(str(item.get("status", "")).upper() for item in items)
            values.update({
                "FAIL_COUNT": counts["FAIL"], "WARN_COUNT": counts["WARN"],
                "PASS_COUNT": counts["PASS"], "TOTAL_COUNT": len(items),
            })
            status_value = dimension_statuses.get(dim_key, "missing")
            if "SECTION_DETAIL" in values:
                values["SECTION_DETAIL"] = _dimension_detail(items, status_value)
            if "SECTION_AUDIT" in values:
                values["SECTION_AUDIT"] = _dimension_audit(dim_key, items, status_value)
            if "DEGRADATION_NOTE" in values:
                status = _dimension_status(status_value)
                values["DEGRADATION_NOTE"] = (
                    "未发现降级或阻断。" if status in READY_STATES else
                    f"维度状态：{_display_dimension_status(status_value)}；说明：{_dimension_reason(status_value)}"
                )
            if "TIMESTAMP" in values:
                values["TIMESTAMP"] = str(base.get("TIMESTAMP") or scan_plan.get("timestamp") or args.scan_date)

        if "SECTION_MATERIALIZATION" in values:
            values["SECTION_MATERIALIZATION"] = _materialization_section(materialization)
        if "TABLE_REDLINE_COVERAGE" in values or "TABLE_REDLINE_MANUAL" in values:
            coverage, manual = _redline_tables(
                _load_redline_mapping(), findings_data, dimension_statuses, materialization,
            )
            values["TABLE_REDLINE_COVERAGE"] = coverage
            values["TABLE_REDLINE_MANUAL"] = manual

        missing = [
            name for name in parse_contract(template)["required"]
            if name not in values or values[name] is None or
            (isinstance(values[name], str) and not values[name].strip())
        ]
        if missing:
            raise ValueError("required values remain incomplete")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"report-values status=failed reason={type(exc).__name__}", file=sys.stderr)
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"report-values status=pass fields={len(values)} missing=0 output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
