#!/usr/bin/env python3
"""Deterministically render and audit every report declared by the manifest."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

if __package__:
    from .audit_render import main as audit_main
    from .build_report_values import main as values_main
    from .cli_contract import CompactArgumentParser
    from .render_template import main as render_main
else:
    from audit_render import main as audit_main
    from build_report_values import main as values_main
    from cli_contract import CompactArgumentParser
    from render_template import main as render_main


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _quiet_call(function: Callable[[list[str]], int], argv: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = function(argv)
    lines = [line for line in output.getvalue().splitlines() if line.strip()]
    return code, lines[-1][:500] if lines else ""


def _report_entries(manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    entries = [(name, value) for name, value in manifest.get("dimensions", {}).items()]
    entries.append(("summary", manifest["summary"]))
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Render and audit the complete report manifest.",
        status_name="report-pipeline",
    )
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--component-name", required=True)
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--scan-date", required=True)
    parser.add_argument("--scan-plan", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--dimension-statuses", type=Path, required=True)
    parser.add_argument("--base-values", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    skill_root = args.skill_root.expanduser().resolve()
    report_root = args.report_root.expanduser().resolve()
    manifest_path = skill_root / "templates" / "report-manifest.yaml"
    required_inputs = (manifest_path, args.scan_plan, args.findings, args.dimension_statuses)
    if any(not path.is_file() for path in required_inputs):
        print("report-pipeline status=blocked reason=input_not_found", file=sys.stderr)
        return 5
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        entries = _report_entries(manifest)
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        print("report-pipeline status=failed reason=invalid_manifest", file=sys.stderr)
        return 4

    reports: list[dict[str, Any]] = []
    overall_code = 0
    for name, entry in entries:
        template = skill_root / "templates" / entry["template"]
        output_pattern = entry["output"].format(
            component_name=args.component_name, date=args.scan_date
        )
        output_relative = Path(output_pattern)
        if output_relative.parts and output_relative.parts[0] == "security-reports":
            output_relative = Path(*output_relative.parts[1:])
        rendered = report_root / output_relative
        values = report_root / "values" / f"{name}.json"
        audit = rendered.with_suffix(rendered.suffix + ".audit.json")

        values_argv = [
            "--template", str(template), "--component-name", args.component_name,
            "--target-path", args.target_path, "--scan-date", args.scan_date,
            "--scan-plan", str(args.scan_plan), "--findings", str(args.findings),
            "--dimension-statuses", str(args.dimension_statuses), "--output", str(values),
        ]
        if args.base_values:
            values_argv.extend(["--base-values", str(args.base_values)])
        values_code, values_status = _quiet_call(values_main, values_argv)
        render_code = audit_code = 5
        render_status = audit_status = "not_run"
        if values_code == 0:
            render_code, render_status = _quiet_call(render_main, [
                "--template", str(template), "--values", str(values),
                "--output", str(rendered), "--strict", "--report-missing",
                "--max-output-bytes", "65536",
            ])
        if render_code == 0:
            audit_code, audit_status = _quiet_call(audit_main, [
                "--rendered", str(rendered), "--template", str(template),
                "--output", str(audit), "--max-residual", "20",
            ])
        reports.append({
            "name": name, "template": str(template), "values": str(values),
            "rendered": str(rendered), "audit": str(audit),
            "values_code": values_code, "render_code": render_code,
            "audit_code": audit_code, "status_lines": {
                "values": values_status, "render": render_status, "audit": audit_status,
            },
        })
        code = max(values_code, render_code, audit_code)
        if code in {4, 5, 6}:
            overall_code = max(overall_code, code)
        elif code == 3 and overall_code == 0:
            overall_code = 3

    status = "ready" if overall_code == 0 else ("warn" if overall_code == 3 else "blocked")
    payload = {
        "artifact_type": "report_pipeline_result", "schema_version": "1.0",
        "status": status, "report_count": len(reports), "reports": reports,
    }
    _atomic_write(args.output, payload)
    stream = sys.stderr if overall_code in {4, 5, 6} else sys.stdout
    print(
        f"report-pipeline status={status} reports={len(reports)} output={args.output}",
        file=stream,
    )
    return overall_code


if __name__ == "__main__":
    raise SystemExit(main())
