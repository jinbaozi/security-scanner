"""Bounded recursive regex search for scanner sessions.

Unlike recursive grep, this command never writes match lines to the terminal.
It stores a compact JSON summary with capped samples and prints one status line.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any


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
) -> dict[str, Any]:
    matched_lines = 0
    matched_files = 0
    unreadable_files = 0
    samples: list[dict[str, Any]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if includes and not any(fnmatch.fnmatch(path.name, item) for item in includes):
            continue
        file_matches = 0
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
        "pattern": pattern.pattern,
        "root": str(root),
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
    parser = argparse.ArgumentParser(description="Run a bounded recursive regex search.")
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--include", default="*")
    parser.add_argument("--max-count", type=int, default=200)
    parser.add_argument("--max-bytes", type=int, default=32768)
    parser.add_argument("--per-file-cap", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print("safe-grep status=blocked reason=root_not_directory", file=sys.stderr)
        return 5
    max_bytes = max(256, args.max_bytes)
    try:
        translated_pattern = translate_posix_classes(args.pattern)
        pattern = re.compile(translated_pattern)
        report = search(
            root,
            pattern,
            includes=[item.strip() for item in args.include.split(",") if item.strip()],
            max_count=max(0, args.max_count),
            max_bytes=max_bytes,
            per_file_cap=max(0, args.per_file_cap),
        )
    except (re.error, ValueError) as exc:
        print(
            f"safe-grep status=failed reason={type(exc).__name__}", file=sys.stderr
        )
        return 4

    report["pattern"] = args.pattern
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
    args.output.write_text(payload, encoding="utf-8")
    print(
        f"safe-grep status=ok matched_files={report['matched_files']} "
        f"matched_lines={report['matched_lines']} samples={report['sample_count']} "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
