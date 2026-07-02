from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_orchestrator_defines_phase_minus_zero_materialization():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    assert "Phase -0: 输入物化" in orchestrator
    assert "scripts/package_materializer.py" in orchestrator
    assert "A-0" in orchestrator
    assert "overall_redline_assurance=blocked" in orchestrator
    assert "dnf builddep" in orchestrator
    assert "root/sudo 授权" in orchestrator


def test_recon_consumes_materialized_source_and_binary_roots():
    recon = (ROOT / "orchestration" / "reconnaissance.md").read_text(encoding="utf-8")

    assert "materialization" in recon
    assert "source_roots" in recon
    assert "binary_roots" in recon
    assert "source_prepped" in recon
    assert "binary_rpm" in recon
    assert "raw_directory" in recon
    assert "Source*.tar" in recon
    assert "不得当作已扫描源码" in recon


def test_reporter_requires_materialization_summary_and_degraded_redline_status():
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    assert "输入物化摘要" in reporter
    assert "builddep_status" in reporter
    assert "prepped source root" in reporter
    assert "binary root" in reporter
    assert "coverage_status" in reporter
    assert "degraded" in reporter
    assert "materialization.status" in reporter


def test_skill_and_preflight_include_rpm_materialization_tools():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    dependency_check = (ROOT / "references" / "dependency-check.md").read_text(encoding="utf-8")

    for text in (skill, dependency_check):
        assert "rpm2cpio" in text
        assert "cpio" in text
        assert "rpmbuild" in text
        assert "dnf" in text
        assert "patch" in text
        assert "tar" in text


def test_terminal_output_contract_is_compact_and_artifact_backed():
    docs = {
        "SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        "orchestrator.md": (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8"),
        "reporter.md": (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8"),
    }

    for name, text in docs.items():
        assert "每个 Phase 最多输出 1 行终端状态" in text, name
        assert "最终终端摘要最多 8 行" in text, name
        assert "不得向终端输出完整 JSON、原始 findings、大段 stdout/stderr 或文件清单" in text, name
        assert "完整数据必须写入 security-reports/" in text, name

    assert "改为终端直接输出 JSON" not in docs["reporter.md"]
