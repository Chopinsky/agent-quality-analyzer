from aqa.report import merge_llm, render_report

MINIMAL = {
    "schema_version": "1.0",
    "mode": "base",
    "target": "/tmp/agent",
    "git": {"repo": False, "head": None, "base": None, "dirty": False},
    "files": [
        {
            "path": "AGENTS.md",
            "metrics": {"tokens": 50, "rules": 3, "conditions": 1, "branching": 2,
                        "tool_refs": 1, "cross_refs": 0, "negatives": 1, "negative_ratio": 0.333,
                        "hedges": 0, "quantifiers": 0, "entropy": 3.5, "section_overlap": 0.0,
                        "template_vars": 0, "sections": 2},
            "findings": [{"file": "AGENTS.md", "rule_id": "missing-stop-conditions",
                          "severity": "warn", "message": "no stop keywords", "line": 1}],
            "rules": [], "headings": [],
        }
    ],
    "conflicts": [{"type": "contradictory-negation", "severity": "error",
                   "files": ["AGENTS.md", "b.md"], "evidence": "ev"}],
    "scores": {"d1": 100, "d2": 100, "d3": 100, "d4": 100, "d5": 100,
               "structural": 96, "conflicts": 92, "overall": 96, "grade": "B"},
    "diff": None,
    "llm": None,
}


def test_render_header_and_scores():
    text = render_report(MINIMAL, "2026-01-01")
    assert text.startswith("# Agent Complexity Report")
    assert "**Mode:** base" in text
    assert "**Generated:** 2026-01-01" in text
    assert "**Overall Score:** 96/100 — Grade B" in text
    assert "| Area | Score | Grade | Weight |" in text
    assert "| Instruction Density & Length | 100 | A | 15% |" in text


def test_render_findings_by_severity():
    text = render_report(MINIMAL, "2026-01-01")
    assert "### Warn" in text
    assert "`AGENTS.md:1` — missing-stop-conditions: no stop keywords" in text


def test_render_conflicts():
    text = render_report(MINIMAL, "2026-01-01")
    assert "contradictory-negation" in text
    assert "files: `AGENTS.md`, `b.md`" in text


def test_merge_llm():
    llm = {"assessment": "healthy", "semantic_conflicts": ["a"], "recommendations": ["b"]}
    merged = merge_llm(MINIMAL, llm)
    assert merged is not MINIMAL
    assert merged["llm"] == llm
    assert "healthy" in render_report(merged, "2026-01-01")


def test_render_without_llm_still_valid():
    text = render_report(MINIMAL, "2026-01-01")
    assert "## Recommendations" in text
