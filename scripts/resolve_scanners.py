#!/usr/bin/env python3
"""Resolve scanner profiles through the registry without dumping registry source."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROFILES = {
    "redline-p0": {
        "elf", "url", "secret", "comment", "fileleak", "permission",
        "crypto", "network", "component-info", "dependency",
    },
    "redline-full": {
        "elf", "url", "secret", "comment", "fileleak", "permission",
        "crypto", "network", "component-info", "dependency", "secure-coding",
        "integrity", "content-compliance",
    },
    "redline-binary": {"elf", "fileleak", "permission", "dependency"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve scanner registry profile.")
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    skill_root = args.skill_root.expanduser().resolve()
    sys.path.insert(0, str(skill_root))
    try:
        from scanners.registry import discover_scanners
        from scanners.registry.resolver import selected_with_dependency_closure, topological_order

        discovered = discover_scanners(skill_root / "scanners")
        declared = PROFILES[args.profile]
        missing = sorted(declared - set(discovered))
        selected = selected_with_dependency_closure(discovered, declared & set(discovered))
        selected_registry = {key: discovered[key] for key in selected}
        order = topological_order(selected_registry)
        status = "fail" if missing else "pass"
        report = {
            "status": status,
            "profile": args.profile,
            "discovered_dimensions": sorted(discovered),
            "selected_dimensions": order,
            "missing_profile_dimensions": missing,
            "scanners": [
                {
                    "id": scanner_id,
                    "prompt_path": str(discovered[scanner_id].scanner_md_path),
                    "meta_path": str(discovered[scanner_id].scanner_md_path.with_name("meta.yaml")),
                }
                for scanner_id in order
            ],
        }
    except (OSError, ValueError) as exc:
        print(f"scanner-registry status=failed reason={type(exc).__name__}", file=sys.stderr)
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"scanner-registry status={status} discovered={len(discovered)} "
        f"selected={len(order)} missing={len(missing)} output={args.output}"
    )
    return 0 if status == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
