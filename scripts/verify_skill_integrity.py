#!/usr/bin/env python3
"""Snapshot and verify the immutable security-scanner skill tree."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from cli_contract import CompactArgumentParser


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def inventory(skill_root: Path) -> dict[str, dict[str, Any]]:
    root = skill_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("skill_root_not_found")
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        name = relative.as_posix()
        if path.is_symlink():
            files[name] = {"type": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files[name] = {"type": "file", "size": path.stat().st_size, "sha256": digest}
    return files


def snapshot(skill_root: Path) -> dict[str, Any]:
    return {
        "artifact_type": "skill_integrity_baseline",
        "schema_version": "1.0",
        "skill_root": str(skill_root.expanduser().resolve()),
        "files": inventory(skill_root),
    }


def verify(skill_root: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    expected = baseline.get("files")
    if not isinstance(expected, dict):
        raise ValueError("invalid_baseline")
    actual = inventory(skill_root)
    expected_names = set(expected)
    actual_names = set(actual)
    added = sorted(actual_names - expected_names)
    removed = sorted(expected_names - actual_names)
    changed = sorted(name for name in expected_names & actual_names if expected[name] != actual[name])
    status = "pass" if not (added or removed or changed) else "critical"
    return {
        "artifact_type": "skill_integrity_verification",
        "schema_version": "1.0",
        "status": status,
        "skill_root": str(skill_root.expanduser().resolve()),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Snapshot or verify a read-only skill tree", status_name="skill-integrity"
    )
    parser.add_argument("command", choices=("snapshot", "verify"))
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "verify" and args.baseline is None:
        parser.error("verify requires --baseline")
    try:
        root = args.skill_root.expanduser().resolve()
        output = args.output.expanduser().resolve(strict=False)
        bundled_root = Path(__file__).resolve().parents[1]
        if output == root or root in output.parents or output == bundled_root or bundled_root in output.parents:
            raise ValueError("skill_root_write_forbidden")
        if args.command == "snapshot":
            payload = snapshot(root)
            _atomic_write(output, payload)
            print(f"skill-integrity status=pass files={len(payload['files'])} output={args.output}")
            return 0
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        payload = verify(root, baseline)
        _atomic_write(output, payload)
        stream = sys.stderr if payload["status"] == "critical" else sys.stdout
        print(
            f"skill-integrity status={payload['status']} changed={len(payload['changed'])} "
            f"added={len(payload['added'])} removed={len(payload['removed'])} output={args.output}",
            file=stream,
        )
        return 6 if payload["status"] == "critical" else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reason = str(exc) if str(exc) == "skill_root_write_forbidden" else type(exc).__name__
        print(f"skill-integrity status=blocked reason={reason}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
