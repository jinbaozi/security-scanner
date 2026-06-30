from scanners.registry.context import ScanContext


def finding(finding_id: str, severity: str, text: str = "abcd") -> dict:
    return {"id": finding_id, "severity": severity, "description": text}


def test_consume_returns_published_findings_as_data():
    context = ScanContext()
    findings = [finding("one", "high")]

    context.publish("network", findings)

    assert context.consume("network", ["high"], 10) == findings


def test_consume_filters_findings_by_severity():
    context = ScanContext()
    context.publish(
        "network",
        [
            finding("critical", "critical"),
            finding("high", "high"),
            finding("low", "low"),
        ],
    )

    result = context.consume("network", ["critical", "high"], 10)

    assert [item["id"] for item in result] == ["critical", "high"]


def test_consume_enforces_token_budget_after_filtering():
    context = ScanContext()
    context.publish(
        "network",
        [
            finding("critical-large", "critical", "a" * 20),
            finding("high-small", "high", "a" * 4),
            finding("medium-small", "medium", "a" * 4),
        ],
    )

    result = context.consume("network", ["critical", "high", "medium"], 2)

    assert [item["id"] for item in result] == ["high-small", "medium-small"]


def test_publish_overwrites_previous_findings_for_same_dim():
    context = ScanContext()
    context.publish("network", [finding("old", "high")])
    context.publish("network", [finding("new", "high")])

    result = context.consume("network", ["high"], 10)

    assert [item["id"] for item in result] == ["new"]


def test_consume_unknown_dim_returns_empty_list():
    context = ScanContext()

    assert context.consume("missing", ["critical", "high"], 10) == []
