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
    6 - excessive residual placeholders create an abort/context risk
"""
from __future__ import annotations

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

from scripts.cli_contract import CompactArgumentParser
from scripts.render_template import (
    PLACEHOLDER_PATTERN,
    collect_placeholders,
    parse_contract,
)


MAX_RESIDUAL_POLICY = 20


def _atomic_write(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _status_line(report: dict[str, Any], output: Path) -> str:
    return (
        f"render-audit status={report['status']} "
        f"reason={report.get('reason', 'none')} "
        f"required={len(report.get('required_unfilled', []))} "
        f"optional={len(report.get('optional_unfilled', []))} "
        f"unknown={len(report.get('unknown_unfilled', []))} "
        f"output={output}"
    )


def _blocked(reason: str, rendered: Path, template: Path | None, **details: Any) -> dict[str, Any]:
    return {
        "artifact_type": "render_audit",
        "schema_version": "1.0",
        "status": "blocked",
        "reason": reason,
        "rendered_file": str(rendered),
        "template_file": str(template) if template else None,
        "required_unfilled": [],
        "optional_unfilled": [],
        "unknown_unfilled": [],
        **details,
    }


def audit(
    rendered_path: Path,
    template_path: Path | None,
    *,
    max_residual: int = 20,
) -> dict[str, Any]:
    """Audit ``rendered_path`` against the optional ``template_path``.

    The function returns a structured report. The ``status`` field is one of
    ``pass``, ``warn`` (optional unfilled), ``fail`` (required unfilled), or
    ``critical`` (residual count exceeds the configured safety limit).
    """
    rendered = rendered_path.read_text(encoding="utf-8")
    residual_occurrences = PLACEHOLDER_PATTERN.findall(rendered)
    residuals = sorted(set(residual_occurrences))

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

    abort_risk = len(residual_occurrences) > max_residual
    if abort_risk:
        status = "critical"
    elif required_unfilled:
        status = "fail"
    elif optional_unfilled or unknown_unfilled:
        status = "warn"
    else:
        status = "pass"

    reason = {
        "critical": "residual_limit_exceeded",
        "fail": "required_placeholders_unfilled",
        "warn": "non_required_placeholders_unfilled",
        "pass": "none",
    }[status]
    return {
        "artifact_type": "render_audit",
        "schema_version": "1.0",
        "rendered_file": str(rendered_path),
        "template_file": str(template_path) if template_path else None,
        "status": status,
        "reason": reason,
        "declared_placeholders": declared,
        "declared_required": contract.get("required", []),
        "declared_optional": contract.get("optional", []),
        "residual_placeholders": residuals,
        "required_unfilled": required_unfilled,
        "optional_unfilled": optional_unfilled,
        "unknown_unfilled": unknown_unfilled,
        "residual_count": len(residual_occurrences),
        "residual_unique_count": len(residuals),
        "max_residual": max_residual,
        "abort_risk": abort_risk,
    }


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Audit a rendered Security Compliance Scanner report.",
        status_name="render-audit",
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
        required=True,
        help="Where to write the audit JSON.",
    )
    parser.add_argument(
        "--max-residual",
        type=int,
        default=20,
        help="Return critical when residual count exceeds this limit.",
    )
    args = parser.parse_args(argv)

    if args.max_residual > MAX_RESIDUAL_POLICY:
        report = _blocked(
            "max_residual_exceeds_policy",
            args.rendered,
            args.template,
            requested_max_residual=args.max_residual,
            policy_max_residual=MAX_RESIDUAL_POLICY,
        )
        _atomic_write(args.output, report)
        print(_status_line(report, args.output))
        return 5
    if args.max_residual < 0:
        report = _blocked("invalid_max_residual", args.rendered, args.template)
        _atomic_write(args.output, report)
        print(_status_line(report, args.output))
        return 5
    if not args.rendered.is_file():
        report = _blocked("rendered_not_found", args.rendered, args.template)
        _atomic_write(args.output, report)
        print(_status_line(report, args.output))
        return 5
    if args.template is not None and not args.template.is_file():
        report = _blocked("template_not_found", args.rendered, args.template)
        _atomic_write(args.output, report)
        print(_status_line(report, args.output))
        return 5

    try:
        report = audit(
            args.rendered,
            args.template,
            max_residual=args.max_residual,
        )
    except (OSError, UnicodeError) as exc:
        report = _blocked(
            "input_read_error",
            args.rendered,
            args.template,
            error_type=type(exc).__name__,
        )
        _atomic_write(args.output, report)
        print(_status_line(report, args.output))
        return 5

    _atomic_write(args.output, report)
    print(_status_line(report, args.output))
    if report["status"] == "critical":
        return 6
    if report["status"] == "fail":
        return 4
    if report["status"] == "warn":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())