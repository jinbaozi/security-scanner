"""In-memory finding exchange between scanner sessions."""
from copy import deepcopy
from typing import Any

from scanners.registry.tokens import truncate_to_budget


COMPACT_FINDING_FIELDS = (
    "id",
    "dimension",
    "file",
    "line",
    "check_item",
    "status",
    "severity",
    "confidence",
    "verdict",
    "detail",
    "evidence",
    "redline_clause",
    "rl_ids",
)
COMPACT_TEXT_LIMIT = 160


def _truncate_text(value: str, limit: int = COMPACT_TEXT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _compact_finding(finding: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for field in COMPACT_FINDING_FIELDS:
        if field not in finding:
            continue
        value = finding[field]
        if field in {"detail", "evidence"} and isinstance(value, str):
            value = _truncate_text(value)
        compact[field] = deepcopy(value)
    return compact


class ScanContext:
    """Store and consume scanner findings by dimension for a single run."""

    def __init__(self) -> None:
        self._findings_by_dim: dict[str, list[dict[str, Any]]] = {}

    def publish(self, dim: str, findings: list[dict[str, Any]]) -> None:
        """Overwrite findings for a scanner dimension."""
        self._findings_by_dim[dim] = deepcopy(findings)

    def all_findings(self) -> list[dict[str, Any]]:
        """Return defensive copies of all published findings."""
        findings: list[dict[str, Any]] = []
        for dim_findings in self._findings_by_dim.values():
            findings.extend(dim_findings)
        return deepcopy(findings)

    def consume(
        self,
        dim: str,
        severity_filter: list[str],
        budget: int,
        *,
        compact: bool = False,
    ) -> list[dict[str, Any]]:
        """Return filtered finding data constrained by token budget."""
        allowed = set(severity_filter)
        filtered = [
            finding
            for finding in self._findings_by_dim.get(dim, [])
            if finding.get("severity") in allowed
        ]
        if compact:
            filtered = [_compact_finding(finding) for finding in filtered]
        return deepcopy(truncate_to_budget(filtered, budget))
