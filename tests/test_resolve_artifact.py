import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "resolve_artifact.py"


def test_resolves_file_list_from_scan_plan_without_guessing_name(tmp_path):
    report_root = tmp_path / "security-reports"
    list_path = report_root / "recon" / "binary-elf-files.txt"
    list_path.parent.mkdir(parents=True)
    elf = tmp_path / "tool"
    elf.write_bytes(bytes([0x7F]) + b"ELFfixture")
    list_path.write_text(f"{elf}\n", encoding="utf-8")
    plan = report_root / "recon" / "scan-plan.normalized.json"
    plan.write_text(json.dumps({"file_lists": {"elf": {"path": "recon/binary-elf-files.txt", "count": 1}}}), encoding="utf-8")
    output = report_root / "recon" / "resolved-elf.json"

    result = subprocess.run([
        sys.executable, str(CLI), "--scan-plan", str(plan), "--report-root",
        str(report_root), "--file-class", "elf", "--output", str(output)
    ], text=True, capture_output=True, check=False)

    assert result.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "ready"
    assert payload["list_path"] == str(list_path.resolve())
    assert payload["declared_count"] == 1


def test_elf_classification_mismatch_blocks_before_probe(tmp_path):
    report_root = tmp_path / "security-reports"
    list_path = report_root / "recon" / "binary-elf-files.txt"
    list_path.parent.mkdir(parents=True)
    text_file = tmp_path / "executable-script"
    text_file.write_text("#!/bin/sh\n", encoding="utf-8")
    list_path.write_text(f"{text_file}\n", encoding="utf-8")
    plan = report_root / "recon" / "scan-plan.normalized.json"
    plan.write_text(json.dumps({"file_lists": {"elf": {"path": "recon/binary-elf-files.txt", "count": 1}}}), encoding="utf-8")
    output = report_root / "resolved.json"

    result = subprocess.run([
        sys.executable, str(CLI), "--scan-plan", str(plan), "--report-root",
        str(report_root), "--file-class", "elf", "--output", str(output)
    ], text=True, capture_output=True, check=False)

    assert result.returncode == 5
    assert "reason=elf_classification_mismatch" in result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked"
    assert payload["invalid_count"] == 1
    assert "invalid_paths" not in payload


def test_missing_file_class_blocks_without_falling_back_to_recursive_scan(tmp_path):
    report_root = tmp_path / "security-reports"
    plan = report_root / "recon" / "scan-plan.normalized.json"
    plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({"file_lists": {}}), encoding="utf-8")
    output = report_root / "resolved.json"

    result = subprocess.run([
        sys.executable, str(CLI), "--scan-plan", str(plan), "--report-root",
        str(report_root), "--file-class", "elf", "--output", str(output)
    ], text=True, capture_output=True, check=False)

    assert result.returncode == 5
    assert "reason=file_list_not_declared" in result.stderr
    assert not output.exists()


def test_rejects_list_reference_outside_report_root(tmp_path):
    report_root = tmp_path / "security-reports"
    outside = tmp_path / "outside.txt"
    outside.write_text("x\n", encoding="utf-8")
    plan = report_root / "recon" / "scan-plan.normalized.json"
    plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({"file_lists": {"elf": {"path": str(outside), "count": 1}}}), encoding="utf-8")

    result = subprocess.run([
        sys.executable, str(CLI), "--scan-plan", str(plan), "--report-root",
        str(report_root), "--file-class", "elf", "--output", str(report_root / "resolved.json")
    ], text=True, capture_output=True, check=False)

    assert result.returncode == 5
    assert "reason=file_list_outside_report_root" in result.stderr
