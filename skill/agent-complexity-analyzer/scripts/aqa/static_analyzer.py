import math
import re
from pathlib import Path

TOOL_NAMES = [
    "bash", "read", "edit", "write", "grep", "glob", "skill", "task",
    "webfetch", "websearch", "question", "todowrite", "apply_patch",
]
CONDITION_WORDS = ["if", "when", "unless", "then", "else", "otherwise"]
NEGATIVE_WORDS = ["do not", "don't", "never", "must not", "shall not", "avoid"]
HEDGE_WORDS = ["should", "maybe", "possibly", "might", "could", "as needed",
               "if applicable", "whenever possible"]
QUANTIFIER_WORDS = ["some", "various", "several", "multiple", "a few", "things", "stuff"]
STOP_WORDS = ["done", "complete", "completed", "exit", "stop", "finished",
              "verify", "verification"]
ERROR_KEYWORDS = ["error", "failure", "fallback", "retry", "edge case", "exception"]
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "for", "to", "of", "in", "on", "at", "by", "with", "from", "as", "is",
    "are", "be", "been", "was", "were", "do", "does", "did", "not", "no",
    "you", "your", "it", "its", "this", "that", "these", "those", "use",
    "must", "should", "will", "can", "may", "all", "any", "each",
}

TOKEN_THRESHOLD = 1000
RULE_THRESHOLD = 30
BRANCH_THRESHOLD = 15
BRANCH_HARD_THRESHOLD = 25
BRANCH_PER_RULE_THRESHOLD = 1.5
TOOL_REF_THRESHOLD = 10
CROSS_REF_THRESHOLD = 5
NEGATIVE_RATIO_THRESHOLD = 0.4
HEDGE_THRESHOLD = 10
QUANTIFIER_THRESHOLD = 5
ENTROPY_THRESHOLD = 5.0
OVERLAP_THRESHOLD = 0.5
TEMPLATE_VAR_RATIO_THRESHOLD = 0.01
FRONTMATTER_TOKEN_THRESHOLD = 200

BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
CODE_FENCE_RE = re.compile(r"^```")
TEMPLATE_VAR_RE = re.compile(r"\{\{.*?\}\}|{%.*?%}")


def token_estimate(text):
    return max(1, round(len(text) / 4))


def normalize(s):
    return re.sub(r"\s+", " ", s).strip().lower().strip(".,;:!?")


def extract_rules(text):
    rules = []
    for i, raw in enumerate(text.splitlines(), start=1):
        bullet = BULLET_RE.match(raw)
        numbered = NUMBERED_RE.match(raw)
        if bullet:
            rules.append({"line": i, "text": normalize(bullet.group(1)), "numbered": False})
        elif numbered:
            rules.append({"line": i, "text": normalize(numbered.group(1)), "numbered": True})
    return rules


def extract_headings(text):
    headings = []
    for i, raw in enumerate(text.splitlines(), start=1):
        m = HEADING_RE.match(raw)
        if m:
            headings.append({"level": len(m.group(1)), "title": normalize(m.group(2)), "line": i})
    return headings


def _count_words(text, words):
    lower = text.lower()
    return sum(len(re.findall(rf"\b{re.escape(w)}\b", lower)) for w in words)


def shannon_entropy(text):
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    if not tokens:
        return 0.0
    counts = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    n = len(tokens)
    return round(-sum((c / n) * math.log2(c / n) for c in counts.values()), 3)


def section_overlaps(text):
    sections = [[]]
    for raw in text.splitlines():
        if HEADING_RE.match(raw):
            sections.append([])
        else:
            sections[-1].append(raw)
    overlaps = []
    for a, b in zip(sections, sections[1:]):
        sa = {t for t in re.findall(r"[a-z0-9']+", " ".join(a).lower()) if t not in STOPWORDS}
        sb = {t for t in re.findall(r"[a-z0-9']+", " ".join(b).lower()) if t not in STOPWORDS}
        if sa and sb:
            overlaps.append(round(len(sa & sb) / len(sa | sb), 3))
        else:
            overlaps.append(0.0)
    return max(overlaps) if overlaps else 0.0


def _frontmatter(text):
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else None


def is_agent_definition(rel_path):
    return (
        rel_path == "SKILL.md"
        or rel_path.endswith("/SKILL.md")
        or any(k in rel_path for k in ("/skills/", "/agents/", "/agent/"))
    )


def analyze_text(text, rel_path):
    rules = extract_rules(text)
    metrics = {
        "tokens": token_estimate(text),
        "rules": len(rules) + len(extract_headings(text)),
        "conditions": _count_words(text, CONDITION_WORDS),
        "branching": 1 + _count_words(text, CONDITION_WORDS),
        "tool_refs": _count_words(text, TOOL_NAMES),
        "cross_refs": len(re.findall(r"\b(?:see|per)\s+(?:the\s+)?(?:section|rule)\b", text.lower())),
        "negatives": _count_words(text, NEGATIVE_WORDS),
        "negative_ratio": 0.0,
        "hedges": _count_words(text, HEDGE_WORDS),
        "quantifiers": _count_words(text, QUANTIFIER_WORDS),
        "entropy": shannon_entropy(text),
        "section_overlap": section_overlaps(text),
        "template_vars": len(TEMPLATE_VAR_RE.findall(text)),
        "sections": len(extract_headings(text)),
    }
    metrics["negative_ratio"] = round(metrics["negatives"] / max(metrics["rules"], 1), 3)
    return metrics, _lint_findings(text, metrics, rel_path)


def _lint_findings(text, metrics, rel_path):
    findings = []

    def add(rule_id, severity, message, line):
        findings.append({"file": rel_path, "rule_id": rule_id, "severity": severity,
                         "message": message, "line": line})

    lines = text.splitlines()
    if metrics["tokens"] > TOKEN_THRESHOLD:
        add("bloat", "warn", f"token estimate {metrics['tokens']} exceeds {TOKEN_THRESHOLD}", 1)
    fence_lines = [i for i, raw in enumerate(lines, 1) if CODE_FENCE_RE.match(raw)]
    if len(fence_lines) % 2 == 1:
        add("unclosed-code-fence", "error", "odd number of code fences", fence_lines[0])
    for i, raw in enumerate(lines, 1):
        if CODE_FENCE_RE.match(raw):
            continue
        if raw.count("`") % 2 == 1:
            add("unclosed-backtick", "warn", "line has an odd number of backtick characters", i)
            break
    h1s = [h for h in extract_headings(text) if h["level"] == 1]
    if len(h1s) > 1:
        add("duplicate-h1", "warn", f"{len(h1s)} H1 headings found", h1s[1]["line"])
    headings = extract_headings(text)
    for h in headings:
        start = h["line"]
        nxt = next((n["line"] for n in headings if n["line"] > start), len(lines) + 1)
        body = "".join(lines[start:nxt - 1])
        if not body.strip():
            add("empty-section", "warn", f"section '{h['title']}' is empty", h["line"])
    if not re.search(r"\b(" + "|".join(STOP_WORDS) + r")\b", text.lower()):
        add("missing-stop-conditions", "warn", "no stop/done/verification keywords found", 1)
    if metrics["template_vars"] > 0 and metrics["template_vars"] / metrics["tokens"] > TEMPLATE_VAR_RATIO_THRESHOLD:
        add("template-variable-density", "warn", f"{metrics['template_vars']} template variables", 1)
    if not re.search(r"\b(" + "|".join(ERROR_KEYWORDS) + r")\b", text.lower()):
        add("missing-edge-case-coverage", "warn", "no error/fallback/retry keywords found", 1)
    if is_agent_definition(rel_path):
        fm = _frontmatter(text)
        if fm is None or not re.search(r"^\s*(name|description)\s*:", fm, re.MULTILINE):
            add("missing-frontmatter", "warn", "agent definition lacks name/description frontmatter", 1)
        elif token_estimate(fm) > FRONTMATTER_TOKEN_THRESHOLD:
            add("oversized-frontmatter", "info", f"frontmatter is {token_estimate(fm)} tokens", 1)
    return findings


def analyze_file(path, rel_path):
    empty = {"tokens": 0, "rules": 0, "conditions": 0, "branching": 1,
             "tool_refs": 0, "cross_refs": 0, "negatives": 0, "negative_ratio": 0.0,
             "hedges": 0, "quantifiers": 0, "entropy": 0.0, "section_overlap": 0.0,
             "template_vars": 0, "sections": 0}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"path": rel_path, "metrics": empty, "rules": [],
                "headings": [],
                "findings": [{"file": rel_path, "rule_id": "unreadable-file", "severity": "warn",
                              "message": f"cannot read file: {exc}", "line": 0}]}
    metrics, findings = analyze_text(text, rel_path)
    return {"path": rel_path, "metrics": metrics, "findings": findings,
            "rules": extract_rules(text), "headings": extract_headings(text)}
