import pytest
from scanners.registry import resolver
from scanners.registry.resolver import CircularDependencyError, topological_order
from scanners.registry.schema import MetaSchema, ConsumeSpec, ReferenceSpec, SessionSpec, FailureSpec


def make_scanner(id: str, consumes: list[str] = None) -> MetaSchema:
    return MetaSchema(
        id=id, name=id, version="1.0.0", description=id,
        consumes=[
            ConsumeSpec(dim=c, inject_as="data",
                       severity_filter=["critical","high"], token_budget=1000)
            for c in (consumes or [])
        ],
        references=[],
        session=SessionSpec(),
        failure=FailureSpec(),
    )


def test_empty_returns_empty():
    assert topological_order({}) == []


def test_no_deps_returns_any_order():
    scanners = {"a": make_scanner("a"), "b": make_scanner("b")}
    order = topological_order(scanners)
    assert set(order) == {"a", "b"}


def test_dependency_ordering():
    scanners = {
        "crypto": make_scanner("crypto", consumes=["elf"]),
        "elf": make_scanner("elf"),
    }
    order = topological_order(scanners)
    assert order.index("elf") < order.index("crypto")


def test_circular_dependency_raises():
    scanners = {
        "a": make_scanner("a", consumes=["b"]),
        "b": make_scanner("b", consumes=["a"]),
    }
    with pytest.raises(CircularDependencyError):
        topological_order(scanners)


def test_self_dependency_raises():
    scanners = {"a": make_scanner("a", consumes=["a"])}
    with pytest.raises(CircularDependencyError):
        topological_order(scanners)


def test_missing_dependency_raises():
    scanners = {"a": make_scanner("a", consumes=["nonexistent"])}
    with pytest.raises(ValueError, match="nonexistent"):
        topological_order(scanners)


def test_selected_scanners_expand_to_dependency_closure_before_ordering():
    scanners = {
        "component-info": make_scanner("component-info", consumes=["crypto"]),
        "crypto": make_scanner("crypto", consumes=["network", "dependency"]),
        "network": make_scanner("network", consumes=["dependency"]),
        "dependency": make_scanner("dependency"),
        "url": make_scanner("url"),
    }

    selected = resolver.selected_with_dependency_closure(scanners, {"component-info"})
    order = topological_order({scanner_id: scanners[scanner_id] for scanner_id in selected})

    assert selected == {"component-info", "crypto", "network", "dependency"}
    assert "url" not in selected
    assert order.index("dependency") < order.index("network")
    assert order.index("network") < order.index("crypto")
    assert order.index("crypto") < order.index("component-info")
