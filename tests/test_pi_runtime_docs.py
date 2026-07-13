from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pi_runtime_limits_are_project_safety_policy_not_claimed_official_limits():
    limits = (ROOT / "references" / "agent-runtime-limits.md").read_text(
        encoding="utf-8"
    )

    assert "项目安全阈值" in limits
    assert "不是 Pi 官方固定上限" in limits
    assert "单次终端输出" in limits
    assert "单次 Read" in limits
    assert "measure_context.py" in limits
    assert "safe_grep.py" in limits
    assert "禁止读取完整报告正文" in limits


def test_abort_recovery_sop_is_checkpoint_driven_and_context_safe():
    recovery = (ROOT / "references" / "abort-recovery.md").read_text(
        encoding="utf-8"
    )

    assert "不要在同一高风险上下文中盲目重试" in recovery
    assert "pi-preflight.json" in recovery
    assert "scan-plan.summary.json" in recovery
    assert "findings-combined.json" in recovery
    assert "--resume" in recovery
    assert "partial" in recovery
    assert "不得读取完整路径列表" in recovery


def test_skill_and_router_reference_pi_runtime_and_recovery_docs():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    router = (ROOT / "orchestration" / "router.md").read_text(encoding="utf-8")

    for text in (skill, router):
        assert "references/agent-runtime-limits.md" in text
        assert "references/abort-recovery.md" in text


def test_render_audit_documents_critical_residual_gate():
    audit = (ROOT / "references" / "render-audit.md").read_text(encoding="utf-8")
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")

    for text in (audit, reporter):
        assert "--max-residual 20" in text
        assert "critical" in text
        assert "退出码 6" in text
