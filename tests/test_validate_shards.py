import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "validate_shards.py"


@pytest.mark.parametrize(
    ("count", "status", "exit_code"),
    [(40, "pass", 0), (45, "warn", 2), (51, "fail", 3)],
)
def test_validate_shards_enforces_absolute_file_limit(
    count, status, exit_code, tmp_path
):
    scan_plan = tmp_path / "scan-plan.json"
    output = tmp_path / "validation.json"
    scan_plan.write_text(
        json.dumps({"source_shards": [{"id": "s1", "file_count": count}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input",
            str(scan_plan),
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
    assert report["status"] == status
    assert report["max_shard_files"] == count


def test_validate_shards_supports_legacy_files_arrays(tmp_path):
    scan_plan = tmp_path / "scan-plan.json"
    output = tmp_path / "validation.json"
    scan_plan.write_text(
        json.dumps({"source_shards": [{"id": 1, "files": list(range(51))}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(scan_plan), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["errors"][0]["reason"] == "shard_file_limit_exceeded"
