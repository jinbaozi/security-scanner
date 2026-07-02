from pathlib import Path

import yaml

from scanners.registry import discover_scanners


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
MANIFEST_PATH = TEMPLATES_DIR / "report-manifest.yaml"


def _load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_all_scanners_have_report_manifest_entries():
    scanners = discover_scanners(ROOT / "scanners")
    manifest = _load_manifest()
    dimension_ids = set(manifest["dimensions"])

    assert dimension_ids == set(scanners.keys())


def test_manifest_templates_exist():
    manifest = _load_manifest()

    for dim_id, entry in manifest["dimensions"].items():
        template_path = TEMPLATES_DIR / entry["template"]
        assert template_path.is_file(), f"{dim_id}: missing template {entry['template']}"


def test_manifest_defines_13_reporting_dimensions_with_unique_templates_and_outputs():
    manifest = _load_manifest()
    dimensions = manifest["dimensions"]

    assert len(dimensions) == 13
    assert len({entry["template"] for entry in dimensions.values()}) == 13
    assert len({entry["output"] for entry in dimensions.values()}) == 13

    for dim_id, entry in dimensions.items():
        assert entry["template"].startswith("report-"), dim_id
        assert entry["template"].endswith(".md"), dim_id
        assert entry["output"].startswith("security-reports/report-"), dim_id
        assert entry["output"].endswith("-{component_name}-{date}.md"), dim_id


def test_manifest_output_patterns_are_unique():
    manifest = _load_manifest()
    outputs = [entry["output"] for entry in manifest["dimensions"].values()]
    outputs.append(manifest["summary"]["output"])

    assert len(outputs) == len(set(outputs))


def test_summary_template_exists_and_has_index_placeholders():
    manifest = _load_manifest()
    summary_template = TEMPLATES_DIR / manifest["summary"]["template"]
    content = summary_template.read_text(encoding="utf-8")

    assert summary_template.is_file()
    assert manifest["summary"]["title"] == "安全合规扫描汇总报告"
    assert "安全合规扫描汇总报告" in content
    assert "{dimension_report_index}" in content
    assert "{dimension_status_summary}" in content
    assert "{redline_coverage_matrix}" in content
    assert "{redline_manual_checklist}" in content


def test_comprehensive_template_requires_13_dimension_index_and_status_summary():
    content = (TEMPLATES_DIR / "report-comprehensive.md").read_text(encoding="utf-8")

    assert "{dimension_report_index}" in content
    assert "{dimension_status_summary}" in content
    assert "必须列出 13 个维度独立详细报告路径" in content
    assert "必须列出 13 个维度状态" in content
    assert "未发现问题" in content
    assert "不适用/降级原因" in content


def test_comprehensive_template_covers_all_13_dimensions():
    content = (TEMPLATES_DIR / "report-comprehensive.md").read_text(encoding="utf-8")

    expected_prefixes = (
        "{elf_",
        "{url_",
        "{secret_",
        "{comment_",
        "{fileleak_",
        "{permission_",
        "{crypto_",
        "{network_",
        "{component-info_",
        "{dependency_",
        "{secure-coding_",
        "{integrity_",
        "{content-compliance_",
    )

    for prefix in expected_prefixes:
        assert prefix in content, f"missing stats placeholder prefix {prefix}"


def test_reporter_documents_a3c_and_mandatory_dimension_reports():
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    assert "A3c" in reporter
    assert "report-manifest.yaml" in reporter
    assert "executed_dimensions" in reporter
    assert "独立详细报告" in reporter
    assert "report-敏感文件泄露" in reporter
    assert "report-文件权限" in reporter


def test_reporter_uses_manifest_reporting_dimensions_not_executed_dimensions_for_outputs():
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    assert "reporting_dimensions = templates/report-manifest.yaml 中全部 13 个维度" in reporter
    assert "executed_dimensions 只表示 Phase 1 实际扫描执行结果" in reporter
    assert "scan_profile 只影响扫描调度强度，不影响最终 13 份维度独立详细报告产物数量" in reporter
    assert "综合 Markdown 报告 + JSON 结构化数据 + 13 份维度独立详细 Markdown 报告" in reporter


def test_reporter_a3c_requires_all_13_dimension_outputs():
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    assert "A3c" in reporter
    assert "综合报告 + JSON + 13 个维度报告" in reporter
    assert "缺任一维度报告即 A3c FAIL" in reporter
    assert "dimension_report_index 必须覆盖 13 个维度" in reporter
    assert "dimension_status_summary 必须覆盖 13 个维度" in reporter
    assert "实际文件清单必须覆盖 13 个维度" in reporter


def test_reporter_removes_old_profile_scoped_report_rules():
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    forbidden_phrases = (
        "当前 profile 对应专项模板",
        "当前 profile 已执行维度的详细发现",
        "Reporter 只为 `executed_dimensions`",
        "仅当前 profile 实际执行或降级的维度",
        "按 profile 渲染维度专项报告",
    )

    for phrase in forbidden_phrases:
        assert phrase not in reporter


def test_skill_phase3_documents_fixed_13_dimension_reports():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "支持 Claude Code / Codex / OpenCode 时遵循同一共享报告契约" in skill
    assert "最终汇总报告 + 13 个维度独立详细报告" in skill
    assert "scan_profile 只影响 Phase 1 扫描调度，不影响 Phase 3 报告产物数量" in skill
    assert "当前 profile 对应的维度专项报告" not in skill


def test_readme_documents_fixed_13_dimension_reports_and_paths():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    manifest = _load_manifest()

    assert "Claude Code、Codex、OpenCode 使用同一共享报告契约" in readme
    assert "最终汇总报告 + 13 个维度独立详细报告" in readme
    assert "报告固定 13 份维度独立详细报告" in readme
    assert "profile 跳过的维度也会生成占位报告" in readme
    assert "不是。当前设计要求" not in readme

    for entry in manifest["dimensions"].values():
        assert entry["output"] in readme


def test_new_dimension_report_templates_exist():
    for template_name in ("report-敏感文件泄露.md", "report-文件权限.md"):
        path = TEMPLATES_DIR / template_name
        content = path.read_text(encoding="utf-8")

        assert path.is_file()
        assert "## 问题汇总" in content
        assert "## 质量审计结果" in content
        assert "## 降级输出说明" in content
