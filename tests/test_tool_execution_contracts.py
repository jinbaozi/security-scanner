import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cli_contract_and_docs_prevent_argument_guessing():
    contracts = json.loads(
        (ROOT / "references" / "tool-cli-contracts.json").read_text(encoding="utf-8")
    )["contracts"]
    reporter = (ROOT / "orchestration" / "reporter.md").read_text(encoding="utf-8")
    recon = (ROOT / "orchestration" / "reconnaissance.md").read_text(encoding="utf-8")

    assert contracts["summarize_scan_plan"]["required_options"] == ["--input", "--output"]
    assert contracts["build_report_values"]["required_options"] == [
        "--template", "--component-name", "--target-path", "--scan-date", "--output"
    ]
    assert "--input \"$REPORT_ROOT/recon/scan-plan.normalized.json\"" in recon
    for option in ("--template", "--target-path", "--scan-date", "--dimension-statuses"):
        assert option in reporter
    assert "REPORT_STATUS` 只能由 builder 计算" in reporter


def test_versioned_regex_files_compile_without_shell_parsing():
    for relative in (
        "scanners/comment/references/malware-keywords.regex",
        "scanners/crypto/references/weak-crypto.regex",
    ):
        pattern = (ROOT / relative).read_text(encoding="utf-8").rstrip("\r\n")
        re.compile(pattern)


def test_elf_scanner_uses_deterministic_probe_instead_of_direct_checksec_invocation():
    scanner = (ROOT / "scanners" / "elf" / "scanner.md").read_text(encoding="utf-8")

    assert "scripts/elf_hardening_probe.py" in scanner
    assert "checksec --file=\"{filepath}\" --output=json" not in scanner
    assert "checksec --file={filepath} --output=json" not in scanner
    assert "checksec 命令崩溃 | 捕获错误，切换到 readelf 降级方案" not in scanner
    assert "checksec 命令崩溃" not in scanner


def test_integrity_scanner_uses_locale_stable_deterministic_rpm_probe():
    scanner = (ROOT / "scanners" / "integrity" / "scanner.md").read_text(encoding="utf-8")
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    for text in (scanner, orchestrator):
        assert "scripts/rpm_integrity_probe.py" in text
        assert "bad_digest" in text and "bad_signature" in text
        assert "不得" in text and "PASS" in text
    assert "LC_ALL=C" in scanner
    assert "verification_status" in scanner


def test_elf_probe_docs_require_batch_checkpoint_and_resume():
    scanner = (ROOT / "scanners" / "elf" / "scanner.md").read_text(encoding="utf-8")
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    for text in (scanner, orchestrator):
        assert "--batch-size 20" in text
        assert "--checkpoint" in text
        assert "--resume" in text
    assert "每个 batch" in scanner


def test_external_tool_state_model_blocks_invocation_and_parse_errors_from_degrading():
    dependency_check = (ROOT / "references" / "dependency-check.md").read_text(encoding="utf-8")
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    for text in (dependency_check, orchestrator):
        for state in (
            "available",
            "missing",
            "broken",
            "invocation_error",
            "parse_error",
            "confirmed_unavailable",
            "user_approved_degraded",
        ):
            assert state in text
        assert "invocation_error/parse_error 不得静默降级" in text
        assert "unavailable_proof" in text
        assert "user_approved_degraded" in text


def test_orchestrator_defines_a1c_tool_execution_audit_for_elf_probe_evidence():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    assert "A1c（Tool Execution Audit）" in orchestrator
    assert "Phase 1.5" in orchestrator and "Verdict" in orchestrator
    assert "elf_files > 0" in orchestrator
    assert "checksec 可用" in orchestrator
    assert "每个 ELF" in orchestrator and "checksec 结果" in orchestrator
    assert "readelf" in orchestrator and "confirmed_unavailable" in orchestrator
    assert "A1c FAIL" in orchestrator
    assert "blocked/unverified" in orchestrator


def test_degraded_dimensions_require_unavailable_proof_or_user_approval_reference():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    assert "`degraded_dimensions` 必须包含" in orchestrator
    assert "unavailable_proof" in orchestrator
    assert "user_approval_ref" in orchestrator
    assert "confirmed_unavailable" in orchestrator


def test_a1c_contract_fails_missing_checksec_results_and_unproven_readelf_fallback():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    assert "有 ELF 输入、checksec 可用但缺少 checksec 结果：A1c FAIL" in orchestrator
    assert "readelf fallback 缺少 confirmed_unavailable proof：A1c FAIL" in orchestrator
    assert "tool invocation_error 或 parse_error 被写成 degraded：A1c FAIL" in orchestrator


def test_result_verification_agent_is_future_extension_not_current_gate():
    orchestrator = (ROOT / "orchestration" / "orchestrator.md").read_text(encoding="utf-8")

    # Result Verification Agent 已从当前执行链路移除；A1c 为唯一强制工具审计门禁。
    assert "Result Verification Agent" not in orchestrator
    assert "未来扩展项" not in orchestrator
    assert "可增加 Result Verification Agent 作为 A1c 的独立复核者" not in orchestrator
    assert "A1c（Tool Execution Audit）" in orchestrator
    assert "强制复核门禁仅有 A1c" in orchestrator
    assert "高风险维度 `elf`、`secret`、`crypto`、`dependency` 优先强制复核" not in orchestrator


def test_elf_docs_treat_results_mode_as_precise_evidence_and_unknown_as_unverified():
    scanner = (ROOT / "scanners" / "elf" / "scanner.md").read_text(encoding="utf-8")
    guide = (ROOT / "scanners" / "elf" / "references" / "checksec-guide.md").read_text(encoding="utf-8")

    assert "selected_mode 仅为摘要字段" in scanner
    assert "准确模式以 `results[].mode` 为准" in scanner
    assert "readelf 输出为空或对应子命令失败" in scanner
    assert "unknown/unverified" in scanner
    assert "不得推导 `No RELRO`、`No canary` 或 `Not fortified`" in guide
