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
    assert report["artifact_type"] == "safe_grep_result"
    assert report["schema_version"] == "1.0"
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


def test_safe_grep_supports_file_lists_and_cli_aliases(tmp_path):
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "listed.txt").write_text("mail marker\n", encoding="utf-8")
    (source_root / "ignored.txt").write_text("mail marker\n", encoding="utf-8")
    files_file = tmp_path / "files.txt"
    files_file.write_text("listed.txt\nmissing.txt\n", encoding="utf-8")
    output = tmp_path / "matches.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern", "mail",
            "--files-file", str(files_file),
            "--base-root", str(source_root),
            "--max-results", "10",
            "--output-json", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["input_mode"] == "files_file"
    assert report["listed_files"] == 2
    assert report["scanned_files"] == 1
    assert report["missing_files"] == 1
    assert report["matched_lines"] == 1
    assert report["samples"][0]["file"] == "listed.txt"


def test_safe_grep_missing_file_list_blocks_without_expanding_scan_scope(tmp_path):
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "would-match.txt").write_text("secret", encoding="utf-8")
    output = tmp_path / "matches.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern", "secret",
            "--files-file", str(tmp_path / "missing-files.txt"),
            "--base-root", str(source_root),
            "--output", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 5
    assert "reason=files_file_not_found" in result.stderr
    assert not output.exists()


def test_safe_grep_reads_regex_from_file_without_shell_quoting(tmp_path):
    source = tmp_path / "sample.c"
    source.write_text("MD5(value) and user's key\n", encoding="utf-8")
    pattern_file = tmp_path / "crypto.regex"
    pattern_file.write_text(r"MD5\(|user's key", encoding="utf-8")
    output = tmp_path / "matches.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern-file", str(pattern_file),
            "--root", str(tmp_path),
            "--include", "*.c",
            "--output", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["pattern_source"] == str(pattern_file.resolve())
    assert report["matched_lines"] == 1
    assert report["samples"][0]["match"].startswith("MD5")


def test_safe_grep_reports_missing_pattern_file_without_traceback(tmp_path):
    output = tmp_path / "matches.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--pattern-file", str(tmp_path / "missing.regex"),
            "--root", str(tmp_path),
            "--output", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 5
    assert "reason=pattern_file_not_found" in result.stderr
    assert not output.exists()


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
