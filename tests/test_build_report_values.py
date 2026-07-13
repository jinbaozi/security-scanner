import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_report_values.py"
RENDER = ROOT / "scripts" / "render_template.py"
AUDIT = ROOT / "scripts" / "audit_render.py"
TEMPLATE = ROOT / "templates" / "report-comprehensive.md"


def test_builder_produces_complete_comprehensive_values_for_empty_scan(tmp_path):
    values = tmp_path / "values.json"
    report = tmp_path / "report.md"
    audit = tmp_path / "audit.json"
    findings = tmp_path / "findings.json"
    scan_plan = tmp_path / "scan-plan.json"
    findings.write_text("[]", encoding="utf-8")
    scan_plan.write_text(json.dumps({"total_files": 3, "scan_files": 3}), encoding="utf-8")

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--scan-plan", str(scan_plan),
            "--findings", str(findings),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert built.returncode == 0
    assert built.stderr == ""
    assert built.stdout.count("\n") == 1

    rendered = subprocess.run(
        [sys.executable, str(RENDER), "--template", str(TEMPLATE), "--values", str(values), "--output", str(report), "--strict"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert rendered.returncode == 0

    audited = subprocess.run(
        [sys.executable, str(AUDIT), "--rendered", str(report), "--template", str(TEMPLATE), "--output", str(audit)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert audited.returncode == 0
    assert json.loads(audit.read_text(encoding="utf-8"))["residual_count"] == 0
