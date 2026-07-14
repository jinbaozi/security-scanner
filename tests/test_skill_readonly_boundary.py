import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts" / "verify_skill_integrity.py"


def test_report_pipeline_rejects_report_root_inside_skill(tmp_path):
    scan_plan = tmp_path / "scan-plan.json"
    findings = tmp_path / "findings.json"
    statuses = tmp_path / "statuses.json"
    result_json = tmp_path / "result.json"
    scan_plan.write_text("{}", encoding="utf-8")
    findings.write_text("[]", encoding="utf-8")
    statuses.write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "report_pipeline.py"),
            "--skill-root", str(ROOT), "--report-root", str(ROOT / "security-reports"),
            "--component-name", "fixture", "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13", "--scan-plan", str(scan_plan),
            "--findings", str(findings), "--dimension-statuses", str(statuses),
            "--output", str(result_json),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 5
    assert "reason=skill_root_write_forbidden" in result.stderr
    assert not (ROOT / "security-reports").exists()


def test_report_pipeline_cannot_use_fake_skill_root_to_bypass_write_guard(tmp_path):
    fake_skill = tmp_path / "fake-skill"
    fake_skill.mkdir()
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "report_pipeline.py"),
            "--skill-root", str(fake_skill), "--report-root", str(ROOT / "security-reports"),
            "--component-name", "fixture", "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13", "--scan-plan", str(tmp_path / "missing-plan.json"),
            "--findings", str(tmp_path / "missing-findings.json"),
            "--dimension-statuses", str(tmp_path / "missing-statuses.json"),
            "--output", str(tmp_path / "result.json"),
        ],
        text=True, capture_output=True, check=False,
    )

    assert result.returncode == 5
    assert "reason=skill_root_mismatch" in result.stderr
    assert not (ROOT / "security-reports").exists()


def test_integrity_cli_detects_modified_skill_file(tmp_path):
    skill_root = tmp_path / "skill"
    report_root = tmp_path / "reports"
    skill_root.mkdir()
    report_root.mkdir()
    protected = skill_root / "SKILL.md"
    protected.write_text("original\n", encoding="utf-8")
    baseline = report_root / "baseline.json"
    verification = report_root / "verification.json"

    snapshot = subprocess.run(
        [sys.executable, str(INTEGRITY), "snapshot", "--skill-root", str(skill_root), "--output", str(baseline)],
        text=True, capture_output=True, check=False,
    )
    assert snapshot.returncode == 0, snapshot.stderr

    protected.write_text("modified\n", encoding="utf-8")
    verify = subprocess.run(
        [
            sys.executable, str(INTEGRITY), "verify", "--skill-root", str(skill_root),
            "--baseline", str(baseline), "--output", str(verification),
        ],
        text=True, capture_output=True, check=False,
    )

    assert verify.returncode == 6
    payload = json.loads(verification.read_text(encoding="utf-8"))
    assert payload["status"] == "critical"
    assert payload["changed"] == ["SKILL.md"]


def test_runtime_docs_forbid_any_skill_root_write():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    router = (ROOT / "orchestration" / "router.md").read_text(encoding="utf-8")

    for text in (skill, router):
        assert "SKILL_ROOT 及其所有子路径均为只读输入" in text
        assert "不得修改" in text
        assert "REPORT_ROOT" in text
