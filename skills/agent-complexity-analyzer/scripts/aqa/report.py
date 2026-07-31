import json

from .scores import WEIGHTS, grade_for

AREA_LABELS = {
    "d1": "Instruction Density & Length",
    "d2": "Branching Factor",
    "d3": "Tool & Constraint Coupling",
    "d4": "Negative Constraints",
    "d5": "Ambiguity / Entropy",
    "structural": "Structural Lint",
    "conflicts": "Conflict Detection",
}
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

SUGGESTIONS = {
    "bloat": "Split the file: move detailed rules into referenced sections or separate files.",
    "unclosed-code-fence": "Close the code fence: every ``` opener needs a matching closer.",
    "unclosed-backtick": "Fix inline code markers: backticks must come in pairs.",
    "duplicate-h1": "Keep a single H1; demote the rest to H2.",
    "empty-section": "Fill or remove empty sections.",
    "missing-stop-conditions": "Add explicit stop/done conditions (e.g., a 'When done' section).",
    "template-variable-density": "Reduce template variables or document each one.",
    "missing-edge-case-coverage": "Add error-handling guidance (failure, fallback, retry).",
    "missing-frontmatter": "Add name and description frontmatter to the agent definition.",
    "oversized-frontmatter": "Trim the frontmatter block.",
    "unreadable-file": "Check file encoding; save as UTF-8.",
    "duplicate-rule": "Remove duplicate rules; keep one authoritative statement.",
    "near-duplicate-rule": "Merge near-identical rules.",
    "contradictory-negation": "Resolve the contradiction: pick one policy and delete the other.",
    "conflicting-scope": "Unify the required/optional policy for the tool.",
    "reference-deadlock": "Break the circular cross-file reference.",
    "priority-ambiguity": "Use one numbering style so priorities are unambiguous.",
}


def _sorted_findings(contract):
    findings = [f for fa in contract["files"] for f in fa["findings"]]
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["file"], f["line"], f["rule_id"]))
    return findings


def merge_llm(contract, llm):
    merged = dict(contract)
    merged["llm"] = llm
    return merged


def render_report(contract, generated_date):
    out = []
    scores = contract["scores"]
    git = contract["git"]
    out.append("# Agent Complexity Report")
    out.append("")
    out.append(f"**Target:** `{contract['target']}`")
    out.append(f"**Mode:** {contract['mode']}")
    out.append(f"**Generated:** {generated_date}")
    out.append(f"**Git:** repo: {'yes' if git['repo'] else 'no'} | head: `{git['head'] or '-'}` | "
               f"base: `{git['base'] or '-'}` | dirty: {'yes' if git['dirty'] else 'no'}")
    out.append("")
    out.append("## Executive Summary")
    out.append("")
    out.append(f"**Overall Score:** {scores['overall']}/100 — Grade {scores['grade']}")
    out.append("")
    findings = _sorted_findings(contract)
    if findings:
        out.append("**Top Findings:**")
        out.append("")
        for f in findings[:3]:
            out.append(f"- `{f['file']}:{f['line']}` [{f['severity']}] {f['rule_id']}: {f['message']}")
        out.append("")
    llm = contract.get("llm")
    if llm and llm.get("assessment"):
        out.append(llm["assessment"])
        out.append("")
    out.append("## Scores")
    out.append("")
    out.append("| Area | Score | Grade | Weight |")
    out.append("|---|---|---|---|")
    for area in ("d1", "d2", "d3", "d4", "d5", "structural", "conflicts"):
        out.append(f"| {AREA_LABELS[area]} | {scores[area]} | {grade_for(scores[area])} | "
                   f"{int(WEIGHTS[area] * 100)}% |")
    out.append("")
    out.append("## Key Metrics")
    out.append("")
    out.append("| File | Tokens | Rules | Branching | Negatives | Neg. Ratio | Hedges | Tools | Entropy |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for fa in contract["files"]:
        m = fa["metrics"]
        out.append(f"| `{fa['path']}` | {m['tokens']} | {m['rules']} | {m['branching']} | "
                   f"{m['negatives']} | {m['negative_ratio']} | {m['hedges']} | {m['tool_refs']} | "
                   f"{m['entropy']} |")
    out.append("")
    out.append("## Findings")
    out.append("")
    for sev in ("error", "warn", "info"):
        out.append(f"### {sev.title()}")
        out.append("")
        sev_findings = [f for f in findings if f["severity"] == sev]
        if sev_findings:
            for f in sev_findings:
                out.append(f"- `{f['file']}:{f['line']}` — {f['rule_id']}: {f['message']}")
        else:
            out.append("_None._")
        out.append("")
    out.append("## Conflicts")
    out.append("")
    if contract["conflicts"]:
        for c in contract["conflicts"]:
            files = ", ".join(f"`{f}`" for f in c["files"])
            out.append(f"- [{c['severity']}] {c['type']} — files: {files} — {c['evidence']}")
    else:
        out.append("_None detected._")
    out.append("")
    if llm and llm.get("semantic_conflicts"):
        out.append("### Semantic conflicts (LLM)")
        out.append("")
        for sc in llm["semantic_conflicts"]:
            out.append(f"- {sc}")
        out.append("")
    if contract["mode"] == "diff" and contract.get("diff"):
        _render_diff(out, contract["diff"])
    out.append("## Recommendations")
    out.append("")
    rule_ids = sorted({f["rule_id"] for f in findings})
    recs = [SUGGESTIONS[r] for r in rule_ids if r in SUGGESTIONS]
    if recs:
        for r in recs:
            out.append(f"- {r}")
    else:
        out.append("- No rule-based recommendations; the agent definition looks healthy.")
    if llm and llm.get("recommendations"):
        for r in llm["recommendations"]:
            out.append(f"- {r}")
    out.append("")
    out.append("## Appendix: Per-File Metrics")
    out.append("")
    out.append("```json")
    out.append(json.dumps([{"path": fa["path"], "metrics": fa["metrics"]} for fa in contract["files"]],
                          indent=2, ensure_ascii=False))
    out.append("```")
    return "\n".join(out) + "\n"


def _render_diff(out, diff):
    out.append("## Diff")
    out.append("")
    for entry in diff["per_file"]:
        out.append(f"### `{entry['path']}`")
        out.append("")
        out.append(f"Lines: +{entry['lines_added']}/-{entry['lines_deleted']} | "
                   f"Rules: +{entry['added_rules']}/-{entry['removed_rules']} | "
                   f"Base present: {entry['base_present']}")
        out.append("")
        out.append("| Metric | Base | Current | Delta |")
        out.append("|---|---|---|---|")
        for key in ("tokens", "rules", "branching", "negatives", "negative_ratio",
                    "hedges", "tool_refs", "entropy", "section_overlap", "template_vars"):
            d = entry["deltas"][key]
            out.append(f"| {key} | {d['base']} | {d['current']} | {d['delta']} |")
        out.append("")
        if entry["added_findings"]:
            out.append("**New findings:**")
            for f in entry["added_findings"]:
                out.append(f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line']})")
            out.append("")
        if entry["removed_findings"]:
            out.append("**Removed findings:**")
            for f in entry["removed_findings"]:
                out.append(f"- {f['rule_id']}: {f['message']} (line {f['line']})")
            out.append("")
    out.append("### Regression Risks")
    out.append("")
    risks = diff["regression_risks"]
    if risks:
        for r in risks:
            out.append(f"- {r}")
    else:
        out.append("_None._")
    out.append("")
