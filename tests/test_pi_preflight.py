import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "pi_preflight.py"


def test_pi_preflight_resolves_skill_resources_outside_skill_cwd(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "preflight.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--target",
            str(target),
            "--output-json",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["scanner_count"] == 13
    assert report["template_count"] == 14
    assert report["skill_root"] == str(ROOT)
    assert report["target_root"] == str(target.resolve())


def test_pi_preflight_reports_missing_python_dependency_without_traceback(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "preflight.json"

    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(CLI),
            "--target",
            str(target),
            "--output-json",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 5
    assert "preflight status=blocked" in result.stderr
    assert "Traceback" not in result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["errors"] == [
        "missing_python_dependency"
    ]


def test_pi_preflight_reports_missing_target_without_traceback(tmp_path):
    missing = tmp_path / "missing"
    output = tmp_path / "preflight.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--target",
            str(missing),
            "--output-json",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 5
    assert "preflight status=blocked" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "blocked"
