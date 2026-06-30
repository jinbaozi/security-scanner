import json
import re
from pathlib import Path
from typing import Any

from scanners.registry import discover_scanners


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIR = ROOT / "tests" / "fixtures" / "expected"
LEGACY_DIMENSION_IDS = (
    "component" + "_info",
    "file" + "_leak",
    "undisclosed" + "_interface",
    "sensitive" + "_file",
)
LEGACY_SCAN_PATHS = (
    ROOT / "templates",
    ROOT / "README.md",
    ROOT / "SKILL.md",
    ROOT / "orchestration",
    ROOT / "scanners",
    ROOT / "tests",
)
GENERATED_CONTRACT_DIRS = {"__pycache__", ".pytest_cache"}

PROMPT_DIMENSION_PATTERNS = (
    re.compile(r'"dimension"\s*:\s*"([^"]+)"'),
    re.compile(r"`dimension`\s*\|\s*固定为\s*`([^`]+)`"),
    re.compile(r"dimension\s+固定为\s*`([^`]+)`"),
)
REFERENCE_PATTERN = re.compile(r"`((?:\.\./\.\./references|references)/[^`\s]+\.md)`")


def _prompt_dimensions(prompt: str) -> list[str]:
    dimensions: list[str] = []
    for pattern in PROMPT_DIMENSION_PATTERNS:
        dimensions.extend(pattern.findall(prompt))
    return dimensions


def _walk_json_values(value: Any, key_name: str) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, item in value.items():
            if key == key_name and isinstance(item, str):
                found.append(item)
            found.extend(_walk_json_values(item, key_name))
        return found
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_walk_json_values(item, key_name))
        return found
    return []


def _contract_text_files(paths: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        files.extend(
            item
            for item in path.rglob("*")
            if item.is_file() and GENERATED_CONTRACT_DIRS.isdisjoint(item.parts)
        )
    return files


def test_scanner_prompt_dimensions_match_meta_ids():
    scanners = discover_scanners(ROOT / "scanners")

    for scanner_id, scanner in scanners.items():
        dimensions = _prompt_dimensions(scanner.prompt)

        assert dimensions, f"{scanner.scanner_md_path} has no fixed dimension examples"
        assert set(dimensions) == {scanner_id}


def test_prompt_reference_paths_match_meta_and_resolve():
    scanners = discover_scanners(ROOT / "scanners")

    for scanner in scanners.values():
        scanner_dir = scanner.scanner_md_path.parent
        meta_paths = {reference.path for reference in scanner.meta.references}
        prompt_paths = set(REFERENCE_PATTERN.findall(scanner.prompt))

        assert prompt_paths <= meta_paths, scanner.scanner_md_path
        for reference_path in meta_paths:
            resolved_path = (scanner_dir / reference_path).resolve()
            assert resolved_path.is_file(), f"{reference_path} from {scanner.meta.id} is missing"


def test_expected_fixture_dimensions_are_current_scanner_ids():
    scanner_ids = set(discover_scanners(ROOT / "scanners"))

    for fixture_path in EXPECTED_DIR.glob("*.json"):
        payload = json.loads(fixture_path.read_text())
        dimensions = _walk_json_values(payload, "dimension")
        scanner_names = _walk_json_values(payload, "scanner")

        for value in dimensions + scanner_names:
            assert value in scanner_ids, f"{fixture_path} uses unknown scanner id {value!r}"


def test_contract_texts_do_not_use_legacy_dimension_ids():
    legacy_pattern = re.compile("|".join(re.escape(item) for item in LEGACY_DIMENSION_IDS))

    for path in _contract_text_files(LEGACY_SCAN_PATHS):
        content = path.read_text(encoding="utf-8", errors="ignore")
        match = legacy_pattern.search(content)

        assert match is None, f"{path.relative_to(ROOT)} uses legacy scanner id {match.group(0)!r}"
