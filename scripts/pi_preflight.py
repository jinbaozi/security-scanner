"""Validate that the security-scanner skill can run from a Pi target cwd.

The script resolves bundled resources from its own location, never from the
caller's current working directory. Detailed checks are written to JSON while
the terminal receives at most one summary line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


def preflight(skill_root: Path, target: Path) -> dict[str, Any]:
    """Return a compact Pi compatibility report for a skill and target."""
    skill_root = skill_root.resolve()
    target = target.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not target.exists():
        errors.append("target_not_found")

    required_paths = (
        "SKILL.md",
        "orchestration/router.md",
        "orchestration/orchestrator.md",
        "orchestration/reporter.md",
        "scanners/registry",
        "templates/report-manifest.yaml",
        "scripts/render_template.py",
        "scripts/audit_render.py",
        "scripts/safe_grep.py",
        "scripts/content_compliance_probe.py",
        "scripts/resolve_scanners.py",
        "scripts/normalize_shards.py",
        "scripts/build_report_values.py",
        "scripts/validate_shards.py",
        "scripts/summarize_scan_plan.py",
        "scripts/measure_context.py",
        "references/agent-runtime-limits.md",
        "references/abort-recovery.md",
        "references/scanner-output-limits.md",
    )
    missing_resources = [
        item for item in required_paths if not (skill_root / item).exists()
    ]
    if missing_resources:
        errors.append("missing_skill_resources")

    scanner_ids: list[str] = []
    manifest_dimensions: list[str] = []
    template_paths = sorted((skill_root / "templates").glob("*.md"))
    contract_errors: list[dict[str, Any]] = []

    if not missing_resources:
        try:
            import yaml

            from scanners.registry import discover_scanners
            from scripts.render_template import collect_placeholders, parse_contract

            scanner_ids = sorted(discover_scanners(skill_root / "scanners"))
            manifest = yaml.safe_load(
                (skill_root / "templates/report-manifest.yaml").read_text(
                    encoding="utf-8"
                )
            )
            manifest_dimensions = sorted(manifest.get("dimensions", {}))
            if scanner_ids != manifest_dimensions:
                errors.append("scanner_manifest_mismatch")

            manifest_templates = [
                entry.get("template")
                for entry in manifest.get("dimensions", {}).values()
            ]
            manifest_templates.append(manifest.get("summary", {}).get("template"))
            missing_templates = sorted(
                name
                for name in manifest_templates
                if not name or not (skill_root / "templates" / name).is_file()
            )
            if missing_templates:
                errors.append("missing_manifest_templates")

            for path in template_paths:
                text = path.read_text(encoding="utf-8")
                contract = parse_contract(text)
                required = set(contract["required"])
                optional = set(contract["optional"])
                used = set(collect_placeholders(text))
                if used != required | optional or required & optional:
                    contract_errors.append(
                        {
                            "template": path.name,
                            "undeclared": sorted(used - required - optional),
                            "unused": sorted((required | optional) - used),
                            "overlap": sorted(required & optional),
                        }
                    )
            if contract_errors:
                errors.append("invalid_template_contract")
        except ModuleNotFoundError:
            errors.append("missing_python_dependency")
        except Exception as exc:  # Convert environment/config faults to JSON.
            errors.append("preflight_exception")
            warnings.append(f"{type(exc).__name__}: {exc}")

    status = "blocked" if errors else ("warn" if warnings else "pass")
    return {
        "status": status,
        "skill_root": str(skill_root),
        "target_root": str(target),
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "scanner_count": len(scanner_ids),
        "manifest_dimension_count": len(manifest_dimensions),
        "template_count": len(template_paths),
        "errors": errors,
        "warnings": warnings,
        "contract_errors": contract_errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Pi skill preflight checks.")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)

    target = args.target.expanduser()
    output = args.output_json
    if output is None:
        base = target if target.is_dir() else target.parent
        output = base / "security-reports" / "pi-preflight.json"

    report = preflight(SKILL_ROOT, target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    line = (
        f"preflight status={report['status']} scanners={report['scanner_count']} "
        f"templates={report['template_count']} output={output}"
    )
    if report["status"] == "blocked":
        print(line, file=sys.stderr)
        return 5
    print(line)
    return 2 if report["status"] == "warn" else 0


if __name__ == "__main__":
    raise SystemExit(main())
