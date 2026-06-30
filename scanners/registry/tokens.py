"""Token budgeting helpers for scanner context findings."""
import json
from typing import Any


SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count with a stable 4 chars/token heuristic."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def _finding_budget_text(finding: dict[str, Any]) -> str:
    for key in ("description", "summary", "title", "message", "details"):
        value = finding.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(finding, ensure_ascii=False, sort_keys=True)


def _finding_tokens(finding: dict[str, Any]) -> int:
    return estimate_tokens(_finding_budget_text(finding))


def truncate_to_budget(
    findings: list[dict[str, Any]],
    budget: int,
) -> list[dict[str, Any]]:
    """Return findings that fit within budget, prioritized by severity then id."""
    if budget <= 0:
        return []

    remaining = budget
    result: list[dict[str, Any]] = []
    sorted_findings = sorted(
        findings,
        key=lambda finding: (
            -SEVERITY_RANK.get(str(finding.get("severity", "info")), 0),
            str(finding.get("id", "")),
        ),
    )

    for finding in sorted_findings:
        finding_tokens = _finding_tokens(finding)
        if finding_tokens <= remaining:
            result.append(finding)
            remaining -= finding_tokens

    return result
