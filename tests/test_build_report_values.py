import json
import subprocess
import sys
from pathlib import Path

from scripts.build_report_values import DIMENSION_PREFIX, build_values


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_report_values.py"
RENDER = ROOT / "scripts" / "render_template.py"
AUDIT = ROOT / "scripts" / "audit_render.py"
TEMPLATE = ROOT / "templates" / "report-comprehensive.md"


def test_report_status_is_pass_when_coverage_is_complete_and_findings_are_pass_only():
    values = build_values(
        "[[REPORT_STATUS]]",
        "fixture",
        "/tmp/fixture",
        "2026-07-13",
        {},
        [{"status": "PASS", "severity": "info", "dimension": "elf", "verdict": "confirmed"}],
        {},
        {dimension: "ready" for dimension in DIMENSION_PREFIX},
    )

    assert values["REPORT_STATUS"] == "PASS"


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
    built_values = json.loads(values.read_text(encoding="utf-8"))
    assert built_values["REPORT_STATUS"] == "UNVERIFIED"
    assert "未验证" in built_values["SECTION_DIMENSION_STATUS"]

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


def test_builder_requires_coverage_status_for_every_dimension_before_pass(tmp_path):
    values = tmp_path / "values.json"
    findings = tmp_path / "findings.json"
    statuses = tmp_path / "dimension-statuses.json"
    findings.write_text("[]", encoding="utf-8")
    statuses.write_text(json.dumps({"elf": "ready"}), encoding="utf-8")

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--findings", str(findings),
            "--dimension-statuses", str(statuses),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert built.returncode == 0
    payload = json.loads(values.read_text(encoding="utf-8"))
    assert payload["REPORT_STATUS"] == "UNVERIFIED"
    assert "口令硬编码：未验证" in payload["SECTION_DIMENSION_STATUS"]


def test_builder_uses_dimension_coverage_and_never_turns_blocked_scan_into_pass(tmp_path):
    values = tmp_path / "values.json"
    findings = tmp_path / "findings.json"
    statuses = tmp_path / "dimension-statuses.json"
    findings.write_text("[]", encoding="utf-8")
    statuses.write_text(
        json.dumps({"elf": {"status": "blocked", "reason": "invocation_error"}, "url": "ready"}),
        encoding="utf-8",
    )

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--findings", str(findings),
            "--dimension-statuses", str(statuses),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert built.returncode == 0
    payload = json.loads(values.read_text(encoding="utf-8"))
    assert payload["REPORT_STATUS"] == "BLOCKED"
    assert "安全编译：已阻断" in payload["SECTION_DIMENSION_STATUS"]
    assert "公网地址：已执行" in payload["SECTION_DIMENSION_STATUS"]
