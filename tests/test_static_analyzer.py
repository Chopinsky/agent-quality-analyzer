from aqa.static_analyzer import (
    analyze_text,
    extract_rules,
    section_overlaps,
    shannon_entropy,
    token_estimate,
)

SIMPLE = """# H

- first rule
- second rule
1. third rule
plain text
"""


def test_token_estimate():
    assert token_estimate("a" * 100) == 25
    assert token_estimate("") == 1


def test_extract_rules():
    rules = extract_rules(SIMPLE)
    assert [(r["line"], r["text"], r["numbered"]) for r in rules] == [
        (3, "first rule", False),
        (4, "second rule", False),
        (5, "third rule", True),
    ]


def test_metrics_basic():
    text = (
        "# My Agent\n\n"
        "- If the user asks, use the bash tool, and stop once done.\n"
        "- If it fails, never retry silently; retry on error.\n"
        "- Then check the output and verify.\n"
    )
    metrics, findings = analyze_text(text, "AGENTS.md")
    assert metrics["rules"] == 4
    assert metrics["conditions"] == 3
    assert metrics["branching"] == 4
    assert metrics["tool_refs"] == 1
    assert metrics["negatives"] == 1
    assert metrics["negative_ratio"] == 0.25
    assert metrics["tokens"] == token_estimate(text)
    assert findings == []


def test_negative_ratio_zero_when_no_rules():
    metrics, _ = analyze_text("plain text without any rules\n", "AGENTS.md")
    assert metrics["rules"] == 0
    assert metrics["negative_ratio"] == 0.0


def test_shannon_entropy():
    assert shannon_entropy("a a b b") == 1.0
    assert shannon_entropy("") == 0.0


def test_section_overlap_high():
    text = (
        "## One\n\nuse the read tool and the grep tool often\n\n"
        "## Two\n\nuse the read tool and the grep tool often\n"
    )
    assert section_overlaps(text) > 0.5
