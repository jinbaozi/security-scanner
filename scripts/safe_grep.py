"""Bounded recursive regex search for scanner sessions.

Unlike recursive grep, this command never writes match lines to the terminal.
It stores a compact JSON summary with capped samples and prints one status line.
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


POSIX_CLASS_REPLACEMENTS = {
    "alnum": "A-Za-z0-9",
    "alpha": "A-Za-z",
    "blank": r" \t",
    "digit": r"\d",
    "lower": "a-z",
    "space": r"\s",
    "upper": "A-Z",
    "word": r"\w",
    "xdigit": "A-Fa-f0-9",
}


def translate_posix_classes(pattern: str) -> str:
    """Translate common POSIX bracket classes to Python ``re`` syntax."""
    translated = pattern
    for name, replacement in POSIX_CLASS_REPLACEMENTS.items():
        translated = translated.replace(f"[:{name}:]", replacement)
    return translated


def search(
    root: Path,
    pattern: re.Pattern[str],
    *,
    includes: list[str],
    max_count: int,
    max_bytes: int,
    per_file_cap: int,
    paths: list[Path] | None = None,
    listed_files: int = 0,
    missing_files: int = 0,
    outside_root_files: int = 0,
) -> dict[str, Any]:
    matched_lines = 0
    matched_files = 0
    unreadable_files = 0
    scanned_files = 0
    samples: list[dict[str, Any]] = []

    candidates = sorted(paths) if paths is not None else sorted(root.rglob("*"))
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        if includes and not any(fnmatch.fnmatch(path.name, item) for item in includes):
            continue
        file_matches = 0
        scanned_files += 1
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                for line_number, line in enumerate(stream, 1):
                    match = pattern.search(line)
                    if match is None:
                        continue
                    matched_lines += 1
                    file_matches += 1
                    if file_matches <= per_file_cap and len(samples) < max_count:
                        samples.append(
                            {
                                "file": str(path.relative_to(root)),
                                "line": line_number,
                                "match": line.rstrip("\r\n")[:240],
                            }
                        )
        except OSError:
            unreadable_files += 1
            continue
        if file_matches:
            matched_files += 1

    report: dict[str, Any] = {
        "artifact_type": "safe_grep_result",
        "schema_version": "1.0",
        "pattern": pattern.pattern,
        "root": str(root),
        "input_mode": "files_file" if paths is not None else "root",
        "listed_files": listed_files,
        "scanned_files": scanned_files,
        "missing_files": missing_files,
        "outside_root_files": outside_root_files,
        "matched_files": matched_files,
        "matched_lines": matched_lines,
        "sample_count": len(samples),
        "samples": samples,
        "truncated": matched_lines > len(samples),
        "limits": {
            "max_count": max_count,
            "max_bytes": max_bytes,
            "per_file_cap": per_file_cap,
        },
        "unreadable_files": unreadable_files,
    }

    # Keep the JSON valid while enforcing the byte budget. Counts remain exact.
    while True:
        payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) <= max_bytes:
            break
        if not report["samples"]:
            raise ValueError("max-bytes is too small for the summary")
        report["samples"].pop()
        report["sample_count"] = len(report["samples"])
        report["truncated"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Run a bounded recursive regex search.",
        status_name="safe-grep",
    )
    patterns = parser.add_mutually_exclusive_group(required=True)
    patterns.add_argument("--pattern")
    patterns.add_argument("--pattern-file", type=Path)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--root", type=Path)
    inputs.add_argument("--files-file", type=Path)
    parser.add_argument("--base-root", type=Path)
    parser.add_argument("--include", default="*")
    parser.add_argument("--max-count", "--max-results", dest="max_count", type=int, default=200)
    parser.add_argument("--max-bytes", type=int, default=32768)
    parser.add_argument("--per-file-cap", type=int, default=20)
    parser.add_argument("--output", "--output-json", dest="output", type=Path, required=True)
    args = parser.parse_args(argv)

    pattern_source = "cli"
    if args.pattern_file:
        pattern_path = args.pattern_file.expanduser().resolve()
        if not pattern_path.is_file():
            print("safe-grep status=blocked reason=pattern_file_not_found", file=sys.stderr)
            return 5
        try:
            raw_pattern = pattern_path.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError:
            print("safe-grep status=blocked reason=pattern_file_unreadable", file=sys.stderr)
            return 5
        if not raw_pattern:
            print("safe-grep status=failed reason=empty_pattern", file=sys.stderr)
            return 4
        pattern_source = str(pattern_path)
    else:
        raw_pattern = args.pattern

    paths: list[Path] | None = None
    listed_files = missing_files = outside_root_files = 0
    if args.root:
        root = args.root.expanduser().resolve()
        if not root.is_dir():
            print("safe-grep status=blocked reason=root_not_directory", file=sys.stderr)
            return 5
    else:
        files_file = args.files_file.expanduser().resolve()
        if not files_file.is_file():
            print("safe-grep status=blocked reason=files_file_not_found", file=sys.stderr)
            return 5
        root = (args.base_root or files_file.parent).expanduser().resolve()
        if not root.is_dir():
            print("safe-grep status=blocked reason=base_root_not_directory", file=sys.stderr)
            return 5
        paths = []
        seen: set[Path] = set()
        for raw_line in files_file.read_text(encoding="utf-8", errors="replace").splitlines():
            value = raw_line.strip()
            if not value or value.startswith("#"):
                continue
            listed_files += 1
            candidate = Path(value).expanduser()
            candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            if not candidate.is_relative_to(root):
                outside_root_files += 1
            elif not candidate.is_file() or candidate.is_symlink():
                missing_files += 1
            else:
                paths.append(candidate)
    max_bytes = max(256, args.max_bytes)
    try:
        translated_pattern = translate_posix_classes(raw_pattern)
        pattern = re.compile(translated_pattern)
        report = search(
            root,
            pattern,
            includes=[item.strip() for item in args.include.split(",") if item.strip()],
            max_count=max(0, args.max_count),
            max_bytes=max_bytes,
            per_file_cap=max(0, args.per_file_cap),
            paths=paths,
            listed_files=listed_files,
            missing_files=missing_files,
            outside_root_files=outside_root_files,
        )
    except (re.error, ValueError) as exc:
        print(
            f"safe-grep status=failed reason={type(exc).__name__}", file=sys.stderr
        )
        return 4

    report["pattern"] = raw_pattern
    report["pattern_source"] = pattern_source
    report["translated_pattern"] = translated_pattern
    while True:
        payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) <= max_bytes:
            break
        if not report["samples"]:
            print("safe-grep status=failed reason=max_bytes_too_small", file=sys.stderr)
            return 4
        report["samples"].pop()
        report["sample_count"] = len(report["samples"])
        report["truncated"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(args.output)
    print(
        f"safe-grep status=ok matched_files={report['matched_files']} "
        f"matched_lines={report['matched_lines']} samples={report['sample_count']} "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
