from aqa.static_analyzer import analyze_text


def test_fenced_code_block_not_backtick_issue():
    text = "# A\n\n```\ncode here\n```\n\n- rule, stop when done, retry on error\n"
    _, findings = analyze_text(text, "AGENTS.md")
    assert all(f["rule_id"] != "unclosed-backtick" for f in findings)


def test_structural_findings():
    text = "# A\n\n# B\n\n## Empty\n\n## Next\n\n- rule\n```\n"
    _, findings = analyze_text(text, "AGENTS.md")
    rule_ids = {f["rule_id"] for f in findings}
    assert "unclosed-code-fence" in rule_ids
    assert "duplicate-h1" in rule_ids
    assert "empty-section" in rule_ids
    fence = [f for f in findings if f["rule_id"] == "unclosed-code-fence"][0]
    assert fence["severity"] == "error"
    assert fence["line"] == 10
    dup = [f for f in findings if f["rule_id"] == "duplicate-h1"][0]
    assert dup["line"] == 3


def test_bloat_finding():
    text = "# A\n\n" + ("- " + "word " * 60 + "\n") * 30
    _, findings = analyze_text(text, "AGENTS.md")
    assert any(f["rule_id"] == "bloat" for f in findings)


def test_missing_stop_conditions_and_edge_cases():
    text = "# A\n\n- just a plain rule with no keywords\n"
    _, findings = analyze_text(text, "AGENTS.md")
    rule_ids = {f["rule_id"] for f in findings}
    assert "missing-stop-conditions" in rule_ids
    assert "missing-edge-case-coverage" in rule_ids


def test_template_variable_density():
    text = "# A\n\n- render {{ template_name }} with {{ max_iterations }} and {{ min_delta }}\n"
    _, findings = analyze_text(text, "AGENTS.md")
    assert any(f["rule_id"] == "template-variable-density" for f in findings)


def test_unclosed_backtick():
    text = "# A\n\n- use `the read tool\n"
    _, findings = analyze_text(text, "AGENTS.md")
    assert any(f["rule_id"] == "unclosed-backtick" for f in findings)


def test_missing_frontmatter_on_skill():
    text = "# Skill\n\n- do one thing, stop when done, retry on error\n"
    _, findings = analyze_text(text, ".claude/skills/x/SKILL.md")
    assert any(f["rule_id"] == "missing-frontmatter" for f in findings)


def test_present_frontmatter_passes():
    text = ("---\nname: x\ndescription: y\n---\n\n"
            "# Skill\n\n- do one thing, stop when done, retry on error\n")
    _, findings = analyze_text(text, ".claude/skills/x/SKILL.md")
    assert all(f["rule_id"] != "missing-frontmatter" for f in findings)


def test_oversized_frontmatter():
    text = "---\nname: x\ndescription: " + "word " * 120 + "\n---\n\n# S\n"
    _, findings = analyze_text(text, ".claude/agents/x.md")
    assert any(f["rule_id"] == "oversized-frontmatter" for f in findings)
