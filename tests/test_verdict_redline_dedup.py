from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_mapping() -> list[dict]:
    content = (ROOT / "references" / "redline-mapping.md").read_text()
    yaml_block = content.split("```yaml", 1)[1].split("```", 1)[0]
    return yaml.safe_load(yaml_block)["redline_mapping"]


def test_redline_mapping_covers_all_40_clauses_for_a3b():
    mapping = _load_mapping()
    clause_ids = [item["clause_id"] for item in mapping]

    assert len(clause_ids) == 40
    assert len(set(clause_ids)) == 40


def test_manual_redline_items_do_not_inject_scanner_dims():
    for item in _load_mapping():
        if item["automation"] == "manual":
            assert item["scanner_dims"] == []
            assert "manual_note" in item


def test_orchestrator_documents_redline_dedup_rules():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text()

    assert "`secret` 优先" in orchestrator
    assert "`MISSING_LOCK_FILE` 仅由 `dependency` 主责产出" in orchestrator
    assert "`secret` 与 `fileleak` 同时命中认证密钥路径" in orchestrator
    assert "`secure-coding` 负责注释包裹代码" in orchestrator


def test_report_template_contains_a3b_coverage_placeholders():
    template = (ROOT / "templates" / "report-comprehensive.md").read_text()

    assert "{redline_coverage_matrix}" in template
    assert "{redline_manual_checklist}" in template
    assert "Redline 40 条覆盖矩阵" in template
