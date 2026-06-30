"""Smoke test: registry discovers all 9 scanners and resolves dependencies.

The orchestrator itself is a markdown prompt (orchestration/orchestrator.md),
not Python code -- its execution is performed by an LLM agent. This test
verifies the underlying machinery (registry + resolver) is in place so the
orchestrator prompt can rely on it.
"""
from scanners.registry import discover_scanners
from scanners.registry.resolver import CircularDependencyError, topological_order


def test_all_9_scanners_discoverable():
    scanners = discover_scanners()
    expected = {
        "comment",
        "url",
        "secret",
        "fileleak",
        "permission",
        "elf",
        "network",
        "crypto",
        "component-info",
    }
    assert set(scanners.keys()) == expected


def test_dependency_order_is_total():
    scanners = discover_scanners()
    order = topological_order({k: v.meta for k, v in scanners.items()})
    assert order.index("elf") < order.index("crypto")
    assert order.index("network") < order.index("crypto")
    assert order.index("elf") < order.index("component-info")
    assert order.index("crypto") < order.index("component-info")


def test_no_circular_dependencies_in_production_layout():
    scanners = discover_scanners()
    try:
        topological_order({k: v.meta for k, v in scanners.items()})
    except CircularDependencyError as e:
        raise AssertionError(f"Production layout has cycles: {e}")
