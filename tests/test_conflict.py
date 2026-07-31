from aqa.conflict import detect_conflicts
from aqa.static_analyzer import analyze_text, extract_headings, extract_rules


def _fa(path, rules_text):
    metrics, findings = analyze_text(rules_text, path)
    return {"path": path, "metrics": metrics, "findings": findings,
            "rules": extract_rules(rules_text), "headings": extract_headings(rules_text)}


def test_duplicate_rule_cross_file():
    fa = [_fa("AGENTS.md", "# A\n\n- keep answers short\n"),
          _fa(".claude/agents/x.md", "# B\n\n- keep answers short\n")]
    assert {c["type"] for c in detect_conflicts(fa)} == {"duplicate-rule"}


def test_duplicate_rule_same_file():
    fa = [_fa("AGENTS.md", "# A\n\n- keep answers short\n- keep answers short\n")]
    assert any(c["type"] == "duplicate-rule" for c in detect_conflicts(fa))


def test_contradictory_negation():
    fa = [_fa("AGENTS.md", "# A\n\n- never use the read tool\n"),
          _fa(".claude/agents/x.md", "# B\n\n- must use the read tool\n")]
    conflicts = detect_conflicts(fa)
    neg = [c for c in conflicts if c["type"] == "contradictory-negation"]
    assert len(neg) == 1
    assert neg[0]["severity"] == "error"
    assert neg[0]["files"] == [".claude/agents/x.md", "AGENTS.md"]


def test_near_duplicate_rule():
    fa = [_fa("AGENTS.md", "# A\n\n- always verify the final answer before responding\n"),
          _fa(".claude/agents/x.md", "# B\n\n- always verify the final answer before you respond\n")]
    assert any(c["type"] == "near-duplicate-rule" for c in detect_conflicts(fa))


def test_reference_deadlock():
    a = "# A\n\n## Section Two\n\n- see Section One before starting\n"
    b = "# B\n\n## Section One\n\n- see Section Two before finishing\n"
    fa = [_fa("AGENTS.md", a), _fa(".claude/agents/x.md", b)]
    assert any(c["type"] == "reference-deadlock" for c in detect_conflicts(fa))


def test_priority_ambiguity():
    fa = [_fa("AGENTS.md", "# A\n\n1. first numbered rule\n2. second numbered rule\n- freeform rule\n- another freeform rule\n")]
    assert any(c["type"] == "priority-ambiguity" for c in detect_conflicts(fa))


def test_conflicting_scope():
    fa = [_fa("AGENTS.md", "# A\n\n- must use the bash tool for builds\n"),
          _fa(".claude/agents/x.md", "# B\n\n- the bash tool is optional; may skip it\n")]
    assert any(c["type"] == "conflicting-scope" for c in detect_conflicts(fa))


def test_no_false_positive_on_distinct_rules():
    fa = [_fa("AGENTS.md", "# A\n\n- format the output nicely\n"),
          _fa(".claude/agents/x.md", "# B\n\n- keep the summary brief\n")]
    assert detect_conflicts(fa) == []


def test_conflicts_sorted_deterministically():
    fa = [_fa("AGENTS.md", "# A\n\n- never use the read tool\n- keep answers short\n"),
          _fa(".claude/agents/x.md", "# B\n\n- must use the read tool\n- keep answers short\n")]
    first = detect_conflicts(fa)
    second = detect_conflicts(fa)
    assert first == second
