import json
from pathlib import Path
from typing import Any

import yaml

from scanners.registry import discover_scanners
from scripts.slice_redline_clauses import load_mapping


ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "references" / "redline-mapping.md"
EXPECTED_DIR = ROOT / "tests" / "fixtures" / "expected"
AUTOMATED_MODES = {"full", "partial"}


def _load_slice(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    body = text.split("```yaml", 1)[1].split("```", 1)[0]
    payload = yaml.safe_load(body)
    return payload["redline_clauses"]


def _walk_findings(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        findings: list[dict[str, Any]] = []
        if "redline_clause" in value or "rl_ids" in value:
            findings.append(value)
        for item in value.values():
            findings.extend(_walk_findings(item))
        return findings
    if isinstance(value, list):
        findings: list[dict[str, Any]] = []
        for item in value:
            findings.extend(_walk_findings(item))
        return findings
    return []


def test_redline_mapping_covers_exactly_40_unique_clauses():
    mapping = load_mapping(MAPPING_PATH)
    clause_ids = [item["clause_id"] for item in mapping]

    assert len(mapping) == 40
    assert len(clause_ids) == len(set(clause_ids))


def test_manual_redline_clauses_have_no_scanner_dims():
    for item in load_mapping(MAPPING_PATH):
        if item["automation"] == "manual":
            assert item.get("scanner_dims", []) == [], item["clause_id"]


def test_automated_redline_clauses_are_present_in_dimension_slices():
    mapping = load_mapping(MAPPING_PATH)
    scanners = discover_scanners(ROOT / "scanners")
    slices = {
        scanner_id: _load_slice(scanner.scanner_md_path.parent / "references" / "redline-clauses.md")
        for scanner_id, scanner in scanners.items()
    }

    for item in mapping:
        if item["automation"] not in AUTOMATED_MODES or not item.get("scanner_dims"):
            continue
        expected = {
            "clause_id": item["clause_id"],
            "rl_ids": item["rl_ids"],
        }
        for scanner_dim in item["scanner_dims"]:
            assert scanner_dim in slices
            assert any(
                str(clause["clause_id"]) == expected["clause_id"]
                and clause["rl_ids"] == expected["rl_ids"]
                for clause in slices[scanner_dim]
            ), f"{scanner_dim} missing {expected}"


def test_expected_fixture_redline_bindings_exist_in_mapping():
    valid_bindings = {
        (item["clause_id"], rl_id)
        for item in load_mapping(MAPPING_PATH)
        for rl_id in item["rl_ids"]
    }

    for fixture_path in EXPECTED_DIR.glob("*.json"):
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        for finding in _walk_findings(payload):
            clause_id = finding.get("redline_clause")
            rl_ids = finding.get("rl_ids", [])

            assert "redline_clause" in finding, fixture_path
            assert "rl_ids" in finding, fixture_path
            if clause_id is None:
                assert rl_ids == []
                continue
            assert rl_ids, f"{fixture_path}: {clause_id} has no rl_ids"
            for rl_id in rl_ids:
                assert (clause_id, rl_id) in valid_bindings, (
                    f"{fixture_path}: invalid redline binding {clause_id} + {rl_id}"
                )
