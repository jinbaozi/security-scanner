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


def test_new_dimension_report_templates_exist():
    for template_name in ("report-敏感文件泄露.md", "report-文件权限.md"):
        path = TEMPLATES_DIR / template_name
        content = path.read_text(encoding="utf-8")

        assert path.is_file()
        assert "## 问题汇总" in content
        assert "## 质量审计结果" in content
        assert "## 降级输出说明" in content
