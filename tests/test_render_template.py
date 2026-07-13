import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit_render import audit
from scripts.render_template import RequiredPlaceholderError, render_template


ROOT = Path(__file__).resolve().parents[1]
RENDER_CLI = ROOT / "scripts" / "render_template.py"
AUDIT_CLI = ROOT / "scripts" / "audit_render.py"

TEMPLATE = """---
required:
  - NAME
  - COUNT
optional:
  - NOTE
---
Name: [[NAME]]
Count: [[COUNT]]
Note: [[NOTE]]
"""


@pytest.mark.parametrize("value", [None, "", "   "])
def test_strict_render_rejects_empty_required_values(value):
    with pytest.raises(RequiredPlaceholderError) as error:
        render_template(TEMPLATE, {"NAME": value, "COUNT": 0}, strict=True)

    assert error.value.missing == ["NAME"]


def test_non_strict_render_preserves_unresolved_values_for_audit():
    rendered, missing, _ = render_template(
        TEMPLATE, {"NAME": None, "COUNT": False}, strict=False
    )

    assert "Name: [[NAME]]" in rendered
    assert "Count: False" in rendered
    assert "Note: [[NOTE]]" in rendered
    assert missing == ["NAME", "NOTE"]


def test_strict_render_accepts_zero_and_false():
    rendered, missing, _ = render_template(
        TEMPLATE, {"NAME": False, "COUNT": 0, "NOTE": "ok"}, strict=True
    )

    assert "Name: False" in rendered
    assert "Count: 0" in rendered
    assert missing == []


def test_strict_cli_returns_four_without_traceback_and_writes_audit_sidecar(tmp_path):
    template_path = tmp_path / "template.md"
    output_path = tmp_path / "report.md"
    template_path.write_text(TEMPLATE, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(RENDER_CLI),
            "--template",
            str(template_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert result.stdout == ""
    assert "render status=failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output_path.exists()
    sidecar = output_path.with_suffix(".md.missing.json")
    assert json.loads(sidecar.read_text(encoding="utf-8"))["required_missing"] == [
        "COUNT",
        "NAME",
    ]


@pytest.mark.parametrize(
    ("rendered", "expected_status", "expected_exit"),
    [
        ("complete", "pass", 0),
        ("[[NOTE]]", "warn", 3),
        ("[[NAME]]", "fail", 4),
    ],
)
def test_audit_cli_exit_codes(rendered, expected_status, expected_exit, tmp_path):
    template_path = tmp_path / "template.md"
    rendered_path = tmp_path / "report.md"
    output_path = tmp_path / "audit.json"
    template_path.write_text(TEMPLATE, encoding="utf-8")
    rendered_path.write_text(rendered, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_CLI),
            "--rendered",
            str(rendered_path),
            "--template",
            str(template_path),
            "--output",
            str(output_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == expected_exit
    assert result.stdout == ""
    assert result.stderr == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == expected_status


def test_render_cli_rejects_oversized_output_without_writing_partial_report(tmp_path):
    template_path = tmp_path / "template.md"
    output_path = tmp_path / "report.md"
    template_path.write_text(
        "---\nrequired:\n  - CONTENT\n---\n[[CONTENT]]", encoding="utf-8"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(RENDER_CLI),
            "--template",
            str(template_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        input=json.dumps({"CONTENT": "x" * 70_000}),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert "reason=output_too_large" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output_path.exists()
    audit = json.loads(
        output_path.with_suffix(".md.render.json").read_text(encoding="utf-8")
    )
    assert audit["actual_bytes"] == 70_000
    assert audit["max_output_bytes"] == 65_536


def test_render_cli_allows_explicit_larger_output_limit(tmp_path):
    template_path = tmp_path / "template.md"
    output_path = tmp_path / "report.md"
    template_path.write_text("[[CONTENT]]", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(RENDER_CLI),
            "--template",
            str(template_path),
            "--output",
            str(output_path),
            "--max-output-bytes",
            "80000",
        ],
        input=json.dumps({"CONTENT": "x" * 70_000}),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_path.stat().st_size == 70_000


def test_audit_cli_marks_excessive_residuals_critical(tmp_path):
    rendered_path = tmp_path / "report.md"
    output_path = tmp_path / "audit.json"
    rendered_path.write_text(
        " ".join(f"[[UNKNOWN_{index}]]" for index in range(21)), encoding="utf-8"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_CLI),
            "--rendered",
            str(rendered_path),
            "--output",
            str(output_path),
            "--max-residual",
            "20",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 6
    assert result.stdout == ""
    assert result.stderr == ""
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "critical"
    assert report["abort_risk"] is True
    assert report["residual_count"] == 21


def test_audit_critical_limit_counts_repeated_occurrences(tmp_path):
    rendered_path = tmp_path / "report.md"
    rendered_path.write_text(" ".join(["[[SAME]]"] * 21), encoding="utf-8")

    report = audit(rendered_path, None, max_residual=20)

    assert report["status"] == "critical"
    assert report["residual_count"] == 21
    assert report["residual_unique_count"] == 1
    assert report["residual_placeholders"] == ["SAME"]


def test_audit_reports_required_optional_and_unknown_residuals(tmp_path):
    template_path = tmp_path / "template.md"
    rendered_path = tmp_path / "report.md"
    template_path.write_text(TEMPLATE, encoding="utf-8")
    rendered_path.write_text(
        "[[NAME]] [[NOTE]] [[UNKNOWN]]", encoding="utf-8"
    )

    report = audit(rendered_path, template_path)

    assert report["status"] == "fail"
    assert report["required_unfilled"] == ["NAME"]
    assert report["optional_unfilled"] == ["NOTE"]
    assert report["unknown_unfilled"] == ["UNKNOWN"]
