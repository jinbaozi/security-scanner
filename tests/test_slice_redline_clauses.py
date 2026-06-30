import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIMS = {
    "comment",
    "component-info",
    "content-compliance",
    "crypto",
    "dependency",
    "elf",
    "fileleak",
    "integrity",
    "network",
    "permission",
    "secret",
    "secure-coding",
    "url",
}


def test_slice_redline_clauses_generates_dim_references(tmp_path: Path):
    scanners_dir = tmp_path / "scanners"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "slice_redline_clauses.py"),
            "--mapping",
            str(ROOT / "references" / "redline-mapping.md"),
            "--scanners-dir",
            str(scanners_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    generated = {
        path.parent.parent.name
        for path in scanners_dir.glob("*/references/redline-clauses.md")
    }
    assert generated == EXPECTED_DIMS

    crypto_slice = scanners_dir / "crypto" / "references" / "redline-clauses.md"
    crypto_text = crypto_slice.read_text()
    assert "clause_id: 5.1.3" in crypto_text
    assert 'rl_ids: ["RL-080", "RL-081", "RL-082", "RL-083", "RL-084"]' in crypto_text
    assert "automation: full" in crypto_text
    assert "profile_min: kylin-redline-p0" in crypto_text
    assert "summary:" in crypto_text

    all_text = "\n".join(
        path.read_text() for path in scanners_dir.glob("*/references/redline-clauses.md")
    )
    assert "clause_id: 1.1.2" not in all_text
    assert "automation: manual" not in all_text
    assert "manual_note:" in all_text
    assert "terminology_pending: true" in all_text
