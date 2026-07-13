"""Safe template renderer for Security Compliance Scanner reports.

Templates use the `[[UPPER_SNAKE_CASE]]` placeholder syntax. This module wraps
``string.Template`` so that a missing placeholder is rendered verbatim instead
of raising ``NameError`` or ``KeyError``. The renderer also extracts the
optional YAML frontmatter ``contract`` so callers can enforce required vs.
optional placeholders.

The design intentionally avoids f-strings and ``str.format``: those either
crash on missing keys or, when combined with curated template prose, raise
``NameError`` because curly braces are syntactically significant in Python.
The ``[[...]]`` delimiter has no special meaning in Python expression context
and round-trips cleanly through ``string.Template``.

Usage:
    from scripts.render_template import render_template, parse_contract

    text, missing, contract = render_template(template_str, values, strict=False)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from string import Template
from typing import Any

if __package__:
    from .cli_contract import CompactArgumentParser
else:
    from cli_contract import CompactArgumentParser


# [[UPPER_SNAKE_CASE]] - safe delimiter; cannot collide with f-string syntax.
PLACEHOLDER_PATTERN = re.compile(r"\[\[([A-Z][A-Z0-9_]*)\]\]")
# Optional YAML frontmatter (between leading --- fences)
FRONTMATTER_PATTERN = re.compile(
    r"\A\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL
)


class RequiredPlaceholderError(ValueError):
    """Raised when strict rendering receives no usable required value."""

    def __init__(self, missing: list[str]):
        self.missing = sorted(missing)
        super().__init__(
            "Required placeholders missing or empty under strict mode: "
            + ", ".join(self.missing)
        )


class SafeReportTemplate(Template):
    """``string.Template`` subclass using ``[[...]]`` as the delimiter.

    The default ``$identifier`` delimiter would still be valid Python and
    could collide with prose such as ``$PATH``. ``[[...]]`` is unambiguous
    and stands out visually during review.
    """

    delimiter = "[["
    pattern = r"""
    \[\[(?:
        (?P<escaped>\[\[) |
        (?P<named>[A-Z][A-Z0-9_]*)  |
        \]\] (?P<braced>) |
        (?P<invalid>)
    )\]\]
    """


def parse_contract(template_str: str) -> dict[str, list[str]]:
    """Extract the optional ``contract`` block from the template frontmatter.

    Returns a dict with keys ``required`` and ``optional`` (lists). Missing
    or malformed frontmatter returns an empty contract so the caller can
    still render but cannot enforce required fields.
    """
    match = FRONTMATTER_PATTERN.match(template_str)
    if not match:
        return {"required": [], "optional": []}
    block = match.group(1)
    contract: dict[str, list[str]] = {"required": [], "optional": []}
    current: str | None = None
    for line in block.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        if stripped.startswith("required:"):
            current = "required"
            continue
        if stripped.startswith("optional:"):
            current = "optional"
            continue
        if current is None:
            continue
        # Items are listed as "  - NAME" or just "  NAME"
        item = stripped.lstrip("- ").strip()
        if item and re.fullmatch(r"[A-Z][A-Z0-9_]*", item):
            contract[current].append(item)
    return contract


def collect_placeholders(template_str: str) -> list[str]:
    """Return all placeholders referenced in the template, in order."""
    seen: list[str] = []
    for m in PLACEHOLDER_PATTERN.finditer(template_str):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def render_template(
    template_str: str,
    values: dict[str, Any],
    *,
    strict: bool = False,
) -> tuple[str, list[str], dict[str, list[str]]]:
    """Render the template using ``values``.

    Parameters
    ----------
    template_str:
        The template body, optionally preceded by a YAML frontmatter.
    values:
        Mapping from placeholder name to replacement value. Values that are
        not strings are converted via ``str()``; ``None`` is treated as
        "no value" and left in place unless ``strict`` is True.
    strict:
        When True, raise ``ValueError`` if any required placeholder from the
        contract is missing or empty. Optional placeholders are always
        allowed to be missing.

    Returns
    -------
    rendered:
        The rendered string. Unresolved placeholders remain as ``[[NAME]]``
        so downstream auditors can flag them.
    missing:
        Sorted list of placeholder names that were not present in ``values``.
    contract:
        The parsed contract (required/optional lists).
    """
    contract = parse_contract(template_str)
    body = FRONTMATTER_PATTERN.sub("", template_str, count=1)

    # None always means unresolved. Required strings containing only
    # whitespace are unresolved too, so safe mode leaves an auditable marker
    # instead of silently producing an apparently complete report.
    string_values = {
        k: str(v) for k, v in values.items() if v is not None
    }
    for name in contract.get("required", []):
        value = string_values.get(name)
        if isinstance(value, str) and not value.strip():
            string_values.pop(name, None)

    used = set(collect_placeholders(body))
    missing = sorted(name for name in used if name not in string_values)
    required_missing = sorted(
        name for name in contract.get("required", []) if name not in string_values
    )

    if strict and required_missing:
        raise RequiredPlaceholderError(required_missing)

    # Always use safe_substitute so unknown extras stay verbatim; the strict
    # check above is the only authoritative guard.
    tmpl = SafeReportTemplate(body)
    rendered = tmpl.safe_substitute(string_values)

    return rendered, missing, contract


def _read_yaml_simple(path: Path) -> dict[str, Any]:
    """Tiny YAML reader for ``key: value`` files (no nested structures).

    The contract frontmatter is real YAML, but the values file passed via
    ``--values`` is intentionally flat so we can use a minimal parser and
    avoid pulling PyYAML as a hard dependency.
    """
    values: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list_key is not None:
            values[current_list_key] = (
                values.get(current_list_key, "")
                + ("\n" if values.get(current_list_key) else "")
                + line[4:]
            )
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                current_list_key = key
                values[key] = ""
            else:
                current_list_key = None
                # Strip surrounding quotes
                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ('"', "'")
                ):
                    value = value[1:-1]
                values[key] = value
    return values


def _read_values_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json" or text.lstrip().startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("values JSON must be an object")
        return data
    return _read_yaml_simple(path)


def main(argv: list[str] | None = None) -> int:
    parser = CompactArgumentParser(
        description="Render a Security Compliance Scanner report template.",
        status_name="render",
    )
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument(
        "--values",
        type=Path,
        help="Flat YAML-style key/value file. If omitted, stdin is read.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=65536,
        help="Reject output larger than this byte limit (default: 65536).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when any required placeholder is missing.",
    )
    parser.add_argument(
        "--report-missing",
        action="store_true",
        help="Write missing placeholders as JSON next to the output file.",
    )
    args = parser.parse_args(argv)

    try:
        template_str = args.template.read_text(encoding="utf-8")
    except OSError:
        print("render status=blocked reason=template_not_found", file=sys.stderr)
        return 5
    if args.values:
        try:
            values = _read_values_file(args.values)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            sidecar = args.output.with_suffix(args.output.suffix + ".values.json")
            sidecar.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "reason": "invalid_values",
                        "values": str(args.values),
                        "error_type": type(exc).__name__,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                f"render status=failed reason=invalid_values sidecar={sidecar}",
                file=sys.stderr,
            )
            return 4
    else:
        # Treat stdin as JSON if it looks like JSON, else blank
        data = sys.stdin.read().strip()
        if not data:
            values = {}
        elif data.startswith("{"):
            values = json.loads(data)
        else:
            # Treat stdin as the values mapping in key=value form, one per line
            values = {}
            for line in data.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    values[k.strip()] = v.strip()

    try:
        rendered, missing, contract = render_template(
            template_str, values, strict=args.strict
        )
    except RequiredPlaceholderError as exc:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "template": str(args.template),
            "output": str(args.output),
            "missing": exc.missing,
            "required_missing": exc.missing,
            "strict": True,
            "status": "failed",
        }
        sidecar = args.output.with_suffix(args.output.suffix + ".missing.json")
        sidecar.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            "render status=failed reason=required_missing "
            f"missing={len(exc.missing)} sidecar={sidecar}",
            file=sys.stderr,
        )
        return 4

    actual_bytes = len(rendered.encode("utf-8"))
    if args.max_output_bytes < 1 or actual_bytes > args.max_output_bytes:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        audit = {
            "template": str(args.template),
            "output": str(args.output),
            "status": "failed",
            "reason": "output_too_large",
            "actual_bytes": actual_bytes,
            "max_output_bytes": args.max_output_bytes,
        }
        sidecar = args.output.with_suffix(args.output.suffix + ".render.json")
        sidecar.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            "render status=failed reason=output_too_large "
            f"bytes={actual_bytes} limit={args.max_output_bytes} sidecar={sidecar}",
            file=sys.stderr,
        )
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    summary = {
        "template": str(args.template),
        "output": str(args.output),
        "missing": missing,
        "contract_required": contract.get("required", []),
        "contract_optional": contract.get("optional", []),
        "strict": args.strict,
    }
    if args.report_missing or missing:
        sidecar = args.output.with_suffix(args.output.suffix + ".missing.json")
        sidecar.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    print(
        f"render status={'ok' if not missing else 'incomplete'} "
        f"missing={len(missing)} required_total={len(contract.get('required', []))} "
        f"output={args.output}"
    )

    if args.strict and missing:
        required_missing = [
            m for m in missing if m in contract.get("required", [])
        ]
        if required_missing:
            return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())