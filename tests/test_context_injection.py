from scanners.registry.context import ScanContext
from scanners.registry.tokens import estimate_tokens


def finding(finding_id: str, severity: str, text: str = "abcd") -> dict:
    return {"id": finding_id, "severity": severity, "description": text}


def test_consume_returns_published_findings_as_data():
    context = ScanContext()
    findings = [finding("one", "high")]

    context.publish("network", findings)

    assert context.consume("network", ["high"], 100) == findings


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

    result = context.consume("network", ["critical", "high"], 100)

    assert [item["id"] for item in result] == ["critical", "high"]


def test_consume_enforces_token_budget_after_filtering():
    context = ScanContext()
    context.publish(
        "network",
        [
            {
                "id": "critical-large",
                "severity": "critical",
                "description": "tiny",
                "evidence": "a" * 1000,
            },
            finding("high-small", "high", "a" * 4),
            finding("medium-small", "medium", "a" * 4),
        ],
    )
    budget = estimate_tokens(str(finding("high-small", "high", "a" * 4)))
    budget += estimate_tokens(str(finding("medium-small", "medium", "a" * 4)))

    result = context.consume("network", ["critical", "high", "medium"], budget)

    assert [item["id"] for item in result] == ["high-small", "medium-small"]


def test_publish_overwrites_previous_findings_for_same_dim():
    context = ScanContext()
    context.publish("network", [finding("old", "high")])
    context.publish("network", [finding("new", "high")])

    result = context.consume("network", ["high"], 100)

    assert [item["id"] for item in result] == ["new"]


def test_publish_defensively_copies_input_findings():
    context = ScanContext()
    findings = [
        {
            "id": "original",
            "severity": "high",
            "description": "abcd",
            "evidence": {"path": "before"},
        }
    ]

    context.publish("network", findings)
    findings.append(finding("added-after-publish", "high"))
    findings[0]["id"] = "mutated"
    findings[0]["evidence"]["path"] = "after"

    result = context.consume("network", ["high"], 100)

    assert len(result) == 1
    assert result[0]["id"] == "original"
    assert result[0]["evidence"]["path"] == "before"


def test_consume_returns_defensive_copies_of_findings():
    context = ScanContext()
    context.publish(
        "network",
        [
            {
                "id": "original",
                "severity": "high",
                "description": "abcd",
                "evidence": {"path": "before"},
            }
        ],
    )

    result = context.consume("network", ["high"], 100)
    result.append(finding("added-after-consume", "high"))
    result[0]["id"] = "mutated"
    result[0]["evidence"]["path"] = "after"

    later_result = context.consume("network", ["high"], 100)

    assert len(later_result) == 1
    assert later_result[0]["id"] == "original"
    assert later_result[0]["evidence"]["path"] == "before"


def test_all_findings_returns_findings_from_all_published_dims():
    context = ScanContext()
    context.publish("network", [finding("network-high", "high")])
    context.publish(
        "crypto",
        [
            finding("crypto-critical", "critical"),
            finding("crypto-medium", "medium"),
        ],
    )

    result = context.all_findings()

    assert [item["id"] for item in result] == [
        "network-high",
        "crypto-critical",
        "crypto-medium",
    ]


def test_all_findings_returns_defensive_copies_of_findings():
    context = ScanContext()
    context.publish(
        "network",
        [
            {
                "id": "original",
                "severity": "high",
                "description": "abcd",
                "evidence": {"path": "before"},
            }
        ],
    )

    result = context.all_findings()
    result.append(finding("added-after-collection", "high"))
    result[0]["id"] = "mutated"
    result[0]["evidence"]["path"] = "after"

    later_result = context.all_findings()

    assert len(later_result) == 1
    assert later_result[0]["id"] == "original"
    assert later_result[0]["evidence"]["path"] == "before"


def test_consume_unknown_dim_returns_empty_list():
    context = ScanContext()

    assert context.consume("missing", ["critical", "high"], 10) == []
