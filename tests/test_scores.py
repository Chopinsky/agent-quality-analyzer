from aqa.scores import compute_scores, grade_for
from aqa.static_analyzer import analyze_text, extract_rules


def _single_file(text):
    metrics, findings = analyze_text(text, "AGENTS.md")
    return {"path": "AGENTS.md", "metrics": metrics, "findings": findings,
            "rules": extract_rules(text)}


def test_grade_for():
    assert grade_for(95) == "A"
    assert grade_for(85) == "B"
    assert grade_for(70) == "C"
    assert grade_for(55) == "D"
    assert grade_for(40) == "F"


def test_error_finding_penalty():
    text = "# H\n\n- one rule, stop when done, retry on error.\n```\n"
    scores = compute_scores([_single_file(text)], [])
    assert scores["structural"] == 92
    assert scores["d4"] == 100
    assert scores["overall"] == 98
    assert scores["grade"] == "A"


def test_negative_ratio_penalty():
    text = "# H\n\n" + "".join(
        f"- do not perform step {i}, stop when done, retry on error.\n" for i in range(5))
    scores = compute_scores([_single_file(text)], [])
    assert scores["d4"] == 83
    assert scores["overall"] < 100


def test_conflict_penalty():
    conflicts = [{"type": "contradictory-negation", "severity": "error",
                  "files": ["a", "b"], "evidence": "x"}]
    scores = compute_scores([], conflicts)
    assert scores["conflicts"] == 92
    assert scores["overall"] == 99


def test_weights_sum_to_one():
    from aqa.scores import WEIGHTS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
