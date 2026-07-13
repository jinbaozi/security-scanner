import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "references" / "tool-cli-contracts.json"
RUNTIME_TOOLS = {
    "pi_preflight",
    "package_materializer",
    "normalize_shards",
    "validate_shards",
    "summarize_scan_plan",
    "resolve_scanners",
    "resolve_artifact",
    "safe_grep",
    "summarize_grep_evidence",
    "content_compliance_probe",
    "elf_hardening_probe",
    "rpm_integrity_probe",
    "measure_context",
    "build_report_values",
    "report_pipeline",
    "render_template",
    "audit_render",
}


def test_machine_contract_covers_every_runtime_tool_and_exit_taxonomy():
    payload = json.loads(CONTRACTS.read_text(encoding="utf-8"))

    assert set(payload["contracts"]) == RUNTIME_TOOLS
    assert payload["exit_codes"] == {
        "success": 0,
        "cli_contract_error": 2,
        "warn_or_degraded": 3,
        "failed": 4,
        "blocked": 5,
        "critical": 6,
    }
    for name, contract in payload["contracts"].items():
        assert contract["status_name"], name
        assert contract["output_artifact_type"], name


def test_every_runtime_cli_rejects_missing_arguments_compactly():
    payload = json.loads(CONTRACTS.read_text(encoding="utf-8"))

    for name, contract in payload["contracts"].items():
        result = subprocess.run(
            [sys.executable, str(ROOT / contract["script"])],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, name
        assert result.stdout == "", name
        assert result.stderr.count("\n") == 1, name
        assert "reason=cli_contract_error" in result.stderr, name
        assert "usage:" not in result.stderr.lower(), name


def test_machine_readable_cli_contract_matches_script_help():
    payload = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"

    for contract in payload["contracts"].values():
        result = subprocess.run(
            [sys.executable, str(ROOT / contract["script"]), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        help_text = result.stdout
        for option in contract.get("required_options", []):
            assert option in help_text
        for group in contract.get("required_option_groups", []):
            for option in group:
                assert option in help_text
        for option in contract.get("forbidden_options", []):
            assert option not in help_text


def test_missing_cli_arguments_emit_one_compact_contract_error():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "summarize_scan_plan.py")],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert "reason=cli_contract_error" in result.stderr
    assert "usage:" not in result.stderr


def test_old_report_builder_interface_is_rejected_without_creating_output(tmp_path):
    output = tmp_path / "values.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_report_values.py"),
            "--report-dir", str(tmp_path),
            "--component-name", "fixture",
            "--overall-status", "PASS",
            "--output", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr.count("\n") == 1
    assert "reason=cli_contract_error" in result.stderr
    assert "--template" in result.stderr
    assert not output.exists()
