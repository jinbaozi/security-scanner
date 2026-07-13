import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "summarize_scan_plan.py"


def test_summarize_scan_plan_bounds_output_and_removes_full_path_arrays(tmp_path):
    long_prefix = "/very/long/materialized/root/that/must/not/reach/pi/context"
    all_files = [
        {"path": f"{long_prefix}/src/dir-{i % 20}/file-{i}.c", "origin": "source_prepped"}
        for i in range(2000)
    ]
    scan_plan = {
        "component_name": "large-package",
        "total_files": 2000,
        "scan_files": 1900,
        "elf_files": all_files[:10],
        "config_files": all_files[10:30],
        "excluded": all_files[30:130],
        "all_files": all_files,
        "source_shards": [
            {"id": i, "files": all_files[i * 100 : (i + 1) * 100]}
            for i in range(20)
        ],
    }
    input_path = tmp_path / "scan-plan.json"
    output_path = tmp_path / "scan-plan.summary.json"
    input_path.write_text(json.dumps(scan_plan), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--sample-size",
            "10",
            "--max-bytes",
            "4096",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    assert output_path.stat().st_size <= 4096
    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["total_files"] == 2000
    assert summary["all_files_count"] == 2000
    assert summary["source_shards_count"] == 20
    assert summary["shard_size_distribution"]["max"] == 100
    assert summary["truncated"] is True
    assert long_prefix not in output_path.read_text(encoding="utf-8")
    assert "all_files" not in summary
    assert "source_shards" not in summary


def test_summarize_scan_plan_supports_compact_file_list_contract(tmp_path):
    scan_plan = {
        "component_name": "compact-package",
        "total_files": 120,
        "scan_files": 100,
        "materialization": {"input_kind": "binary_rpm", "status": "ready"},
        "file_lists": {
            "all": {"path": "recon/all-files.txt", "count": 120, "samples": ["src/a.c"]},
            "elf": {"path": "recon/elf-files.txt", "count": 7, "samples": ["bin/app"]},
            "config": {"path": "recon/config-files.txt", "count": 3, "samples": ["etc/app.conf"]},
            "dependency": {"path": "recon/dependency-files.txt", "count": 2, "samples": ["go.mod"]},
            "excluded": {"path": "recon/excluded.jsonl", "count": 20, "samples": ["vendor/a.c"]},
        },
        "source_shards": [
            {"id": 0, "file_list": "recon/shards/source-000.txt", "file_count": 50, "samples": ["src/a.c"]},
            {"id": 1, "file_list": "recon/shards/source-001.txt", "file_count": 50, "samples": ["src/b.c"]},
        ],
    }
    input_path = tmp_path / "scan-plan.normalized.json"
    output_path = tmp_path / "scan-plan.summary.json"
    input_path.write_text(json.dumps(scan_plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(input_path), "--output", str(output_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["artifact_type"] == "scan_plan_summary"
    assert summary["all_files_count"] == 120
    assert summary["elf_count"] == 7
    assert summary["config_count"] == 3
    assert summary["dependency_count"] == 2
    assert summary["excluded_count"] == 20
    assert summary["source_shards_count"] == 2
    assert summary["samples"]["elf"] == ["bin/app"]


def test_summarize_scan_plan_rejects_materialization_payload(tmp_path):
    input_path = tmp_path / "materialization.json"
    output_path = tmp_path / "summary.json"
    input_path.write_text(
        json.dumps({"input_kind": "binary_rpm", "source_roots": [], "binary_roots": [], "status": "ready"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(input_path), "--output", str(output_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert "reason=wrong_input_schema" in result.stderr
    assert not output_path.exists()


def test_summarize_scan_plan_invalid_json_has_compact_error(tmp_path):
    input_path = tmp_path / "scan-plan.json"
    output_path = tmp_path / "summary.json"
    input_path.write_text("{", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(input_path), "--output", str(output_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert "scan-plan-summary status=failed" in result.stderr
    assert "Traceback" not in result.stderr
