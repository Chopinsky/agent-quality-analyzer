WEIGHTS = {"d1": 0.15, "d2": 0.15, "d3": 0.10, "d4": 0.15, "d5": 0.15,
           "structural": 0.20, "conflicts": 0.10}
SEVERITY_PENALTY = {"error": 8, "warn": 4, "info": 1}
AREA_BY_RULE = {
    "bloat": "d1",
    "oversized-frontmatter": "d3",
    "unclosed-code-fence": "structural",
    "unclosed-backtick": "structural",
    "duplicate-h1": "structural",
    "empty-section": "structural",
    "missing-stop-conditions": "structural",
    "template-variable-density": "structural",
    "missing-edge-case-coverage": "structural",
    "missing-frontmatter": "structural",
    "unreadable-file": "structural",
}


def grade_for(score):
    for grade, low in (("A", 90), ("B", 80), ("C", 65), ("D", 50)):
        if score >= low:
            return grade
    return "F"


def _clamp(value):
    return max(0, min(100, value))


def score_file(file_analysis):
    m = file_analysis["metrics"]
    penalties = {area: 0 for area in WEIGHTS}
    for finding in file_analysis["findings"]:
        area = AREA_BY_RULE.get(finding["rule_id"])
        if area:
            penalties[area] += SEVERITY_PENALTY[finding["severity"]]
    if m["tokens"] > 1000:
        penalties["d1"] += 10
    if m["rules"] > 30:
        penalties["d1"] += 10
    if m["branching"] > 25:
        penalties["d2"] += 20
    elif m["branching"] > 15:
        penalties["d2"] += 10
    if m["rules"] and m["branching"] / m["rules"] > 1.5:
        penalties["d2"] += 5
    if m["tool_refs"] > 10:
        penalties["d3"] += 10
    if m["cross_refs"] > 5:
        penalties["d3"] += 5
    if m["negative_ratio"] > 0.4:
        penalties["d4"] += min(30, round((m["negative_ratio"] - 0.4) * 40))
    if m["negatives"] > 10:
        penalties["d4"] += 10
    if m["hedges"] > 10:
        penalties["d5"] += 10
    if m["quantifiers"] > 5:
        penalties["d5"] += 5
    if m["entropy"] > 5.0:
        penalties["d5"] += 5
    if m["section_overlap"] > 0.5:
        penalties["d5"] += 10
    return {area: _clamp(100 - penalties[area]) for area in WEIGHTS}


def compute_scores(file_analyses, conflicts):
    if not file_analyses:
        area_scores = {area: 100 for area in WEIGHTS}
    else:
        per_file = [score_file(fa) for fa in file_analyses]
        area_scores = {area: round(sum(f[area] for f in per_file) / len(per_file))
                       for area in ("d1", "d2", "d3", "d4", "d5", "structural")}
    conflict_penalty = sum(SEVERITY_PENALTY[c["severity"]] for c in conflicts)
    area_scores["conflicts"] = _clamp(100 - conflict_penalty)
    overall = round(sum(area_scores[a] * w for a, w in WEIGHTS.items()))
    return {**area_scores, "overall": overall, "grade": grade_for(overall)}
