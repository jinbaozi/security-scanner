import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "report_pipeline.py"


def test_report_pipeline_renders_and_audits_every_manifest_template(tmp_path):
    report_root = tmp_path / "security-reports"
    report_root.mkdir()
    scan_plan = report_root / "scan-plan.json"
    findings = report_root / "findings.json"
    statuses = report_root / "dimension-statuses.json"
    scan_plan.write_text(json.dumps({"total_files": 0, "file_lists": {}, "source_shards": []}), encoding="utf-8")
    findings.write_text(json.dumps({"findings": []}), encoding="utf-8")
    dimensions = yaml.safe_load((ROOT / "templates/report-manifest.yaml").read_text(encoding="utf-8"))["dimensions"]
    statuses.write_text(json.dumps({name: {"status": "unverified", "reason": "fixture"} for name in dimensions}), encoding="utf-8")
    summary = report_root / "report-pipeline.json"

    result = subprocess.run([
        sys.executable, str(CLI), "--skill-root", str(ROOT), "--report-root",
        str(report_root), "--component-name", "fixture", "--target-path", str(tmp_path),
        "--scan-date", "2026-07-13", "--scan-plan", str(scan_plan), "--findings",
        str(findings), "--dimension-statuses", str(statuses), "--output", str(summary)
    ], text=True, capture_output=True, check=False)

    assert result.returncode in {0, 3}
    assert result.stdout.count("\n") == 1
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["report_count"] == 14
    assert len(payload["reports"]) == 14
    for report in payload["reports"]:
        assert Path(report["rendered"]).is_file()
        assert Path(report["audit"]).is_file()
