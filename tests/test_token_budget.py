from scanners.registry.tokens import estimate_tokens, truncate_to_budget


def finding(finding_id: str, severity: str, text: str) -> dict:
    return {"id": finding_id, "severity": severity, "description": text}


def test_estimate_tokens_empty_string_is_zero():
    assert estimate_tokens("") == 0


def test_estimate_tokens_uses_four_char_heuristic():
    assert estimate_tokens("a" * 100) == 25


def test_estimate_tokens_scales_linearly_for_repeated_strings():
    assert estimate_tokens("a" * 1000) == estimate_tokens("a" * 100) * 10


def test_truncate_to_budget_returns_empty_for_non_positive_budget():
    findings = [finding("a", "critical", "a" * 20)]

    assert truncate_to_budget(findings, 0) == []
    assert truncate_to_budget(findings, -1) == []


def test_truncate_to_budget_prioritizes_severity_descending():
    findings = [
        finding("low", "low", "a" * 4),
        finding("critical", "critical", "a" * 4),
        finding("high-b", "high", "a" * 4),
        finding("medium", "medium", "a" * 4),
        finding("high-a", "high", "a" * 4),
        finding("info", "info", "a" * 4),
    ]

    budget = sum(estimate_tokens(str(item)) for item in findings)
    result = truncate_to_budget(findings, budget)

    assert [item["id"] for item in result] == [
        "critical",
        "high-a",
        "high-b",
        "medium",
        "low",
        "info",
    ]


def test_truncate_to_budget_skips_findings_that_exceed_remaining_budget():
    findings = [
        {
            "id": "critical-large",
            "severity": "critical",
            "description": "tiny",
            "evidence": "a" * 1000,
        },
        finding("high-small", "high", "a" * 4),
        finding("medium-small", "medium", "a" * 4),
    ]
    budget = estimate_tokens(str(findings[1])) + estimate_tokens(str(findings[2]))

    result = truncate_to_budget(findings, budget)

    assert [item["id"] for item in result] == ["high-small", "medium-small"]


def test_truncate_to_budget_counts_full_finding_data_not_description_only():
    finding_with_large_data = {
        "id": "huge",
        "severity": "critical",
        "description": "tiny",
        "evidence": "a" * 1000,
    }
    budget = estimate_tokens(finding_with_large_data["description"])

    assert truncate_to_budget([finding_with_large_data], budget) == []
