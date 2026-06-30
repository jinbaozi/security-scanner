"""Topological dependency resolution for scanners. See plan Task 1."""
from typing import Any

from scanners.registry.schema import MetaSchema


class CircularDependencyError(ValueError):
    pass


def _meta_for(scanner: Any) -> MetaSchema:
    if isinstance(scanner, MetaSchema):
        return scanner
    return scanner.meta


def topological_order(scanners: dict[str, Any]) -> list[str]:
    """Return scanner IDs in dependency-first order."""
    scanner_meta = {
        scanner_id: _meta_for(scanner)
        for scanner_id, scanner in scanners.items()
    }

    for scanner_id, meta in scanner_meta.items():
        for consume in meta.consumes:
            if consume.dim not in scanners:
                raise ValueError(
                    f"scanner {scanner_id!r} consumes unknown dim {consume.dim!r}"
                )

    in_degree = {scanner_id: 0 for scanner_id in scanners}
    dependents: dict[str, list[str]] = {scanner_id: [] for scanner_id in scanners}
    for scanner_id, meta in scanner_meta.items():
        for consume in meta.consumes:
            dependents[consume.dim].append(scanner_id)
            in_degree[scanner_id] += 1

    queue = sorted(scanner_id for scanner_id, degree in in_degree.items() if degree == 0)
    order: list[str] = []

    while queue:
        scanner_id = queue.pop(0)
        order.append(scanner_id)
        for dependent in sorted(dependents[scanner_id]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
        queue.sort()

    if len(order) != len(scanners):
        cycle_nodes = sorted(scanner_id for scanner_id, degree in in_degree.items() if degree > 0)
        raise CircularDependencyError(
            f"circular dependency detected involving: {cycle_nodes}"
        )

    return order
