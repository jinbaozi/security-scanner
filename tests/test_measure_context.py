import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "measure_context.py"


@pytest.mark.parametrize(
    ("size", "risk", "exit_code"),
    [(30_000, "low", 0), (120_000, "medium", 3), (330_000, "critical", 6)],
)
def test_measure_context_classifies_file_backed_inputs(size, risk, exit_code, tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"x" * size)
    output = tmp_path / "context-risk.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--phase",
            "phase-1",
            "--inputs",
            str(artifact),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == exit_code
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["risk_level"] == risk
    assert report["estimated_tokens"] == (size + 2) // 3
    assert report["inputs"][0]["bytes"] == size
    assert "content" not in report["inputs"][0]


def test_measure_context_missing_input_is_auditable_warning(tmp_path):
    output = tmp_path / "context-risk.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--phase",
            "phase-2",
            "--inputs",
            str(tmp_path / "missing.json"),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["risk_level"] == "medium"
    assert report["warnings"] == ["input_not_found"]
