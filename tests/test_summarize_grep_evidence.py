import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "summarize_grep_evidence.py"


def _write_input(path: Path, samples: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "artifact_type": "safe_grep_result",
                "schema_version": "1.0",
                "matched_files": 2,
                "matched_lines": len(samples),
                "samples": samples,
                "truncated": False,
            }
        ),
        encoding="utf-8",
    )


def test_evidence_summary_consumes_match_field_and_bounds_content(tmp_path):
    source = tmp_path / "grep.json"
    output = tmp_path / "review.json"
    _write_input(
        source,
        [
            {"file": "a.c", "line": 2, "match": "backdoor keyword"},
            {"file": "b.c", "line": 7, "match": "malware keyword"},
        ],
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(source), "--output", str(output), "--sample-size", "1"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "grep_evidence_summary"
    assert payload["candidate_count"] == 2
    assert payload["samples"] == [{"file": "a.c", "line": 2, "match": "backdoor keyword"}]
    assert payload["requires_review"] is True


def test_evidence_summary_rejects_unknown_sample_schema_without_traceback(tmp_path):
    source = tmp_path / "grep.json"
    output = tmp_path / "review.json"
    _write_input(source, [{"file": "a.c", "line": 2, "content": "old field"}])

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(source), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert "reason=wrong_input_schema" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()
