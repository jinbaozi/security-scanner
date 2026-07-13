import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "content_compliance_probe.py"


def test_content_probe_keeps_raw_matches_out_of_compact_summary(tmp_path):
    source_root = tmp_path / "src"
    source_root.mkdir()
    source = source_root / "messages.txt"
    source.write_text("prefix blocked-marker suffix\n", encoding="utf-8")
    files_file = tmp_path / "files.txt"
    files_file.write_text("messages.txt\n", encoding="utf-8")
    rules = tmp_path / "rules.md"
    rules.write_text("## Test category\n| Pattern | Note |\n|---|---|\n| `blocked-marker` | test |\n", encoding="utf-8")
    summary = tmp_path / "summary.json"
    evidence = tmp_path / "raw.jsonl"

    result = subprocess.run(
        [
            sys.executable, str(CLI),
            "--rules", str(rules),
            "--files-file", str(files_file),
            "--base-root", str(source_root),
            "--output-summary", str(summary),
            "--evidence-output", str(evidence),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    compact_text = summary.read_text(encoding="utf-8")
    assert "blocked-marker" not in compact_text
    report = json.loads(compact_text)
    assert report["original_count"] == 1
    assert report["emitted_count"] == 1
    assert report["matches"][0]["rule_id"] == "CC-001"
    assert report["matches"][0]["file"] == "messages.txt"
    assert "blocked-marker" in evidence.read_text(encoding="utf-8")
    assert evidence.stat().st_mode & 0o777 == 0o600


def test_content_probe_scans_resource_paths_without_exposing_matched_name(tmp_path):
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "special-map.asset").write_text("neutral\n", encoding="utf-8")
    files_file = tmp_path / "files.txt"
    files_file.write_text("special-map.asset\n", encoding="utf-8")
    rules = tmp_path / "rules.md"
    rules.write_text("## Resource\n```regex\nspecial-map\n```\n", encoding="utf-8")
    summary = tmp_path / "summary.json"
    evidence = tmp_path / "raw.jsonl"

    result = subprocess.run(
        [sys.executable, str(CLI), "--rules", str(rules), "--files-file", str(files_file), "--base-root", str(source_root), "--output-summary", str(summary), "--evidence-output", str(evidence)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    compact_text = summary.read_text(encoding="utf-8")
    assert "special-map" not in compact_text
    report = json.loads(compact_text)
    assert report["original_count"] == 1
    assert report["matches"][0]["file"] == "<redacted-path>"
    assert "special-map.asset" in evidence.read_text(encoding="utf-8")
