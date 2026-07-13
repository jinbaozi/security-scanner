import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "references" / "tool-cli-contracts.json"


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
