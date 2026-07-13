import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "safe_grep.py"


def test_safe_grep_writes_bounded_json_and_only_one_terminal_line(tmp_path):
    source = tmp_path / "many.txt"
    source.write_text("".join(f"secret value {i}\n" for i in range(500)))
    output = tmp_path / "matches.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern",
            "secret",
            "--root",
            str(tmp_path),
            "--include",
            "*.txt",
            "--max-count",
            "5",
            "--max-bytes",
            "1024",
            "--per-file-cap",
            "3",
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
    assert output.stat().st_size <= 1024
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["matched_lines"] == 500
    assert report["matched_files"] == 1
    assert len(report["samples"]) == 3
    assert report["truncated"] is True


def test_safe_grep_translates_posix_character_classes_without_warning(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("alpha beta 123\nno-space-marker\n", encoding="utf-8")
    output = tmp_path / "matches.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern",
            "[[:space:]][[:digit:]]+",
            "--root",
            str(tmp_path),
            "--include",
            "*.txt",
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["matched_lines"] == 1
    assert report["pattern"] == "[[:space:]][[:digit:]]+"
    assert report["translated_pattern"] == r"[\s][\d]+"


def test_safe_grep_reports_invalid_pattern_without_traceback(tmp_path):
    output = tmp_path / "matches.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern",
            "(",
            "--root",
            str(tmp_path),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert "safe-grep status=failed" in result.stderr
    assert "Traceback" not in result.stderr
