import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "resolve_scanners.py"


def test_resolve_scanners_writes_compact_profile_plan(tmp_path):
    output = tmp_path / "registry-plan.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--skill-root",
            str(ROOT),
            "--profile",
            "redline-binary",
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["status"] == "pass"
    assert plan["profile"] == "redline-binary"
    assert set(plan["selected_dimensions"]) == {"elf", "fileleak", "permission", "dependency"}
    assert len(plan["discovered_dimensions"]) == 13
    assert all("scanner.md" in item["prompt_path"] for item in plan["scanners"])
    assert all("prompt" not in item for item in plan["scanners"])
