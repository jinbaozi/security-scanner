"""Post-render audit for Security Compliance Scanner reports.

After a template is rendered, this helper scans the output for residual
``[[UPPER_SNAKE_CASE]]`` placeholders, checks the template contract for
required fields, and reports any unfilled placeholders. The reporter
orchestrator calls this script (or imports its ``audit`` function) before
treating the report as final.

Exit codes:
    0 - audit passed (all required placeholders replaced; no residuals)
    3 - optional placeholders left unreplaced (WARN)
    4 - required placeholders left unreplaced (FAIL)
    5 - audit cannot proceed (missing input, etc.)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Allow `python3 scripts/audit_render.py ...` from the project root by
# ensuring the project root is on sys.path when this file is invoked
# directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.render_template import (
    PLACEHOLDER_PATTERN,
    collect_placeholders,
    parse_contract,
)


def audit(rendered_path: Path, template_path: Path | None) -> dict[str, Any]:
    """Audit ``rendered_path`` against the optional ``template_path``.

    The function returns a structured report. The ``status`` field is one of
    ``pass``, ``warn`` (optional unfilled), or ``fail`` (required unfilled).
    """
    rendered = rendered_path.read_text(encoding="utf-8")
    residuals = sorted(set(PLACEHOLDER_PATTERN.findall(rendered)))

    contract = {"required": [], "optional": []}
    declared: list[str] = []
    if template_path is not None and template_path.exists():
        template_text = template_path.read_text(encoding="utf-8")
        contract = parse_contract(template_text)
        declared = collect_placeholders(template_text)

    required_unfilled = sorted(
        n for n in residuals if n in contract.get("required", [])
    )
    optional_unfilled = sorted(
        n for n in residuals if n in contract.get("optional", [])
    )
    # Anything residual that is not in the contract is "unknown" - still bad.
    unknown_unfilled = sorted(
        n
        for n in residuals
        if n not in contract.get("required", []) and n not in contract.get("optional", [])
    )

    if required_unfilled:
        status = "fail"
    elif optional_unfilled or unknown_unfilled:
        status = "warn"
    else:
        status = "pass"

    return {
        "rendered_file": str(rendered_path),
        "template_file": str(template_path) if template_path else None,
        "status": status,
        "declared_placeholders": declared,
        "declared_required": contract.get("required", []),
        "declared_optional": contract.get("optional", []),
        "residual_placeholders": residuals,
        "required_unfilled": required_unfilled,
        "optional_unfilled": optional_unfilled,
        "unknown_unfilled": unknown_unfilled,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a rendered Security Compliance Scanner report."
    )
    parser.add_argument("--rendered", type=Path, required=True)
    parser.add_argument(
        "--template",
        type=Path,
        help="Original template path (used to recover the contract).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Where to write the audit JSON. Defaults to stdout.",
    )
    args = parser.parse_args(argv)

    if not args.rendered.exists():
        print(f"rendered file not found: {args.rendered}", file=sys.stderr)
        return 5

    report = audit(args.rendered, args.template)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)

    if report["status"] == "fail":
        return 4
    if report["status"] == "warn":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())