import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "normalize_shards.py"


def test_normalize_shards_splits_file_lists_at_absolute_limit(tmp_path):
    report_root = tmp_path / "security-reports"
    shard_dir = report_root / "recon" / "shards"
    shard_dir.mkdir(parents=True)
    source = shard_dir / "source-000.txt"
    source.write_text("".join(f"src/f{i}.c\n" for i in range(51)), encoding="utf-8")
    plan_path = report_root / "recon" / "scan-plan.json"
    output = report_root / "recon" / "scan-plan.normalized.json"
    plan_path.write_text(json.dumps({"source_shards": [{"id": "source-000", "file_list": "recon/shards/source-000.txt", "file_count": 51, "origin_counts": {"source_prepped": 51}}]}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(plan_path), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    normalized = json.loads(output.read_text(encoding="utf-8"))
    assert [item["file_count"] for item in normalized["source_shards"]] == [50, 1]
    assert sum(item["file_count"] for item in normalized["source_shards"]) == 51
    for item in normalized["source_shards"]:
        assert (report_root / item["file_list"]).is_file()
