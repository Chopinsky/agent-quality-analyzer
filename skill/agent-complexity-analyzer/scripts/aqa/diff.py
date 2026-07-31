import subprocess
from pathlib import Path

from .conflict import detect_conflicts
from .discovery import discover_agent_files
from .static_analyzer import analyze_text, extract_headings, extract_rules


class DiffError(Exception):
    pass


def run_git(target, args):
    proc = subprocess.run(["git"] + args, cwd=str(target), capture_output=True, text=True)
    if proc.returncode != 0:
        raise DiffError(proc.stderr.strip() or proc.stdout.strip() or "git command failed")
    return proc.stdout


def is_git_repo(target):
    try:
        run_git(target, ["rev-parse", "--is-inside-work-tree"])
        return True
    except DiffError:
        return False


def git_info(target):
    try:
        head = run_git(target, ["rev-parse", "--short", "HEAD"]).strip()
        dirty = bool(run_git(target, ["status", "--porcelain"]).strip())
        return {"repo": True, "head": head, "dirty": dirty}
    except DiffError:
        return {"repo": False, "head": None, "dirty": False}


def base_content(target, rel_path, base):
    try:
        return run_git(target, ["show", f"{base}:{rel_path}"])
    except DiffError:
        return None


def line_counts(target, rel_path, base):
    try:
        out = run_git(target, ["diff", "--numstat", base, "--", rel_path])
    except DiffError:
        return 0, 0
    parts = out.split()
    if len(parts) >= 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return 0, 0
    return 0, 0


def _analyses(target, rels, base, use_base):
    analyses = []
    for rel in rels:
        if use_base:
            text = base_content(target, rel, base)
            if text is None:
                continue
        else:
            text = Path(target, rel).read_text(encoding="utf-8", errors="replace")
        metrics, findings = analyze_text(text, rel)
        analyses.append({"path": rel, "metrics": metrics, "findings": findings,
                         "rules": extract_rules(text), "headings": extract_headings(text)})
    return analyses


def diff_analysis(target, base="HEAD"):
    target = Path(target)
    if not is_git_repo(target):
        raise DiffError("target is not a git repository")
    try:
        run_git(target, ["rev-parse", "--verify", f"{base}^{{commit}}"])
    except DiffError:
        raise DiffError(f"cannot resolve base ref '{base}'")

    rels = [str(p.relative_to(target)).replace("\\", "/") for p in discover_agent_files(target)]
    current = _analyses(target, rels, base, False)
    base_res = _analyses(target, rels, base, True)
    current_by_path = {a["path"]: a for a in current}
    base_by_path = {a["path"]: a for a in base_res}

    per_file = []
    for rel in rels:
        cur = current_by_path.get(rel)
        bse = base_by_path.get(rel)
        if cur is None:
            continue
        base_metrics = bse["metrics"] if bse else {k: 0 for k in cur["metrics"]}
        base_findings = bse["findings"] if bse else []
        base_rules_n = len(bse["rules"]) if bse else 0

        deltas = {k: {"base": base_metrics[k], "current": cur["metrics"][k],
                      "delta": round(cur["metrics"][k] - base_metrics[k], 3)}
                  for k in cur["metrics"]}

        def fkey(f):
            return (f["rule_id"], f["message"], f["line"])

        cur_keys = {fkey(f) for f in cur["findings"]}
        base_keys = {fkey(f) for f in base_findings}
        added_findings = [f for f in cur["findings"] if fkey(f) not in base_keys]
        removed_findings = [f for f in base_findings if fkey(f) not in cur_keys]

        per_file.append({
            "path": rel,
            "base_present": bse is not None,
            "deltas": deltas,
            "added_rules": max(0, len(cur["rules"]) - base_rules_n),
            "removed_rules": max(0, base_rules_n - len(cur["rules"])),
            "added_findings": added_findings,
            "removed_findings": removed_findings,
            "lines_added": 0,
            "lines_deleted": 0,
        })
    for entry in per_file:
        entry["lines_added"], entry["lines_deleted"] = line_counts(target, entry["path"], base)

    risks = _regression_risks(per_file, current, base_res)
    return {"per_file": per_file, "regression_risks": risks}


def _regression_risks(per_file, current, base_res):
    risks = []
    for entry in per_file:
        d = entry["deltas"]
        tokens = d["tokens"]
        if tokens["base"] and tokens["delta"] / tokens["base"] >= 0.20:
            risks.append(f"{entry['path']}: token estimate up {tokens['delta']} (base {tokens['base']})")
        branching = d["branching"]
        if branching["base"] and branching["delta"] / branching["base"] >= 0.20:
            risks.append(f"{entry['path']}: branching up {branching['delta']} (base {branching['base']})")
        if d["negatives"]["delta"] > 0:
            risks.append(f"{entry['path']}: {d['negatives']['delta']} negative constraint(s) added")
        if d["negative_ratio"]["delta"] > 0:
            risks.append(f"{entry['path']}: negative constraint ratio up {d['negative_ratio']['delta']}")
        if any(f["rule_id"] == "missing-stop-conditions" for f in entry["added_findings"]):
            risks.append(f"{entry['path']}: stop conditions lost")
        if any(f["severity"] == "error" for f in entry["added_findings"]):
            risks.append(f"{entry['path']}: new error-severity finding(s)")
    base_conflicts = detect_conflicts(base_res)
    current_conflicts = detect_conflicts(current)
    if len(current_conflicts) > len(base_conflicts):
        risks.append(f"conflict count increased from {len(base_conflicts)} to {len(current_conflicts)}")
    return risks
