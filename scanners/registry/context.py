"""In-memory finding exchange between scanner sessions."""
from copy import deepcopy
from typing import Any

from scanners.registry.tokens import truncate_to_budget


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
    ) -> list[dict[str, Any]]:
        """Return filtered finding data constrained by token budget."""
        allowed = set(severity_filter)
        filtered = [
            finding
            for finding in self._findings_by_dim.get(dim, [])
            if finding.get("severity") in allowed
        ]
        return deepcopy(truncate_to_budget(filtered, budget))
