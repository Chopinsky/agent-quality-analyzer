from aqa.static_analyzer import analyze_text


def test_fenced_code_block_not_backtick_issue():
    text = "# A\n\n```\ncode here\n```\n\n- rule, stop when done, retry on error\n"
    _, findings = analyze_text(text, "AGENTS.md")
    assert all(f["rule_id"] != "unclosed-backtick" for f in findings)
