import re
from difflib import SequenceMatcher

from .static_analyzer import normalize

NEGATIVE_MARKERS = ["do not", "don't", "never", "must not", "shall not", "avoid"]
REQUIRE_MARKERS = ["must", "always", "required", "shall"]
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "for", "to", "of", "in", "on", "at", "by", "with", "from", "as",
    "is", "are", "be", "been", "was", "were", "do", "does", "did",
    "not", "no", "you", "your", "it", "its", "this", "that", "use",
    "must", "always", "required", "shall", "never", "avoid",
}
TOOL_RE = re.compile(r"\b(bash|read|edit|write|grep|glob|skill|task|webfetch|websearch|question)\b")
SECTION_REF_RE = re.compile(
    r"\b(?:see|per)\s+(?:the\s+)?(section|rule)\s+([a-z0-9' -]+?)"
    r"(?=\s+(?:before|when|after|if|unless|then|and|or)\b|$)",
    re.IGNORECASE,
)
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}


def _content_words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower())
            if len(w) > 2 and w not in STOPWORDS}


def detect_conflicts(file_analyses):
    conflicts = []
    all_rules = [(fa["path"], r["line"], r["text"], r["numbered"])
                 for fa in file_analyses for r in fa.get("rules", [])]

    seen = {}
    for file, line, text, numbered in all_rules:
        if text in seen:
            prev_file, prev_line = seen[text]
            conflicts.append({
                "type": "duplicate-rule", "severity": "warn",
                "files": sorted({prev_file, file}),
                "evidence": f"identical rule '{text}' at {prev_file}:{prev_line} and {file}:{line}",
            })
        seen.setdefault(text, (file, line))

    for i in range(len(all_rules)):
        for j in range(i + 1, len(all_rules)):
            f1, l1, t1, n1 = all_rules[i]
            f2, l2, t2, n2 = all_rules[j]
            if t1 == t2 or min(len(t1), len(t2)) < 10:
                continue
            if min(len(t1), len(t2)) / max(len(t1), len(t2)) > 0.85:
                ratio = SequenceMatcher(None, t1, t2).ratio()
                if ratio > 0.85:
                    conflicts.append({
                        "type": "near-duplicate-rule", "severity": "warn",
                        "files": sorted({f1, f2}),
                        "evidence": f"near-duplicate rules ('{t1}' vs '{t2}', similarity {ratio:.2f})",
                    })
            neg1 = any(m in t1 for m in NEGATIVE_MARKERS)
            neg2 = any(m in t2 for m in NEGATIVE_MARKERS)
            if neg1 != neg2:
                neg, req, fneg, lneg, freq, lreq = (
                    (t1, t2, f1, l1, f2, l2) if neg1 else (t2, t1, f2, l2, f1, l1))
                if any(m in req for m in REQUIRE_MARKERS):
                    shared = _content_words(neg) & _content_words(req)
                    if len(shared) >= 2:
                        conflicts.append({
                            "type": "contradictory-negation", "severity": "error",
                            "files": sorted({fneg, freq}),
                            "evidence": (f"'{neg}' ({fneg}:{lneg}) contradicts "
                                         f"'{req}' ({freq}:{lreq}); shared terms: {sorted(shared)}"),
                        })

    headings = [(fa["path"], h["title"]) for fa in file_analyses for h in fa.get("headings", [])]

    def resolve(file, ref_title):
        same = [h for h in headings if h[0] == file and h[1] == ref_title]
        if not same:
            same = [h for h in headings if h[0] == file and h[1].endswith(ref_title)]
        if same:
            return file
        cross = [h for h in headings if h[0] != file and (h[1] == ref_title or h[1].endswith(ref_title))]
        return cross[0][0] if cross else None

    edges = set()
    for file, line, text, numbered in all_rules:
        for m in SECTION_REF_RE.finditer(text):
            target = resolve(file, normalize(m.group(2)))
            if target:
                edges.add((file, target))
    for a, b in sorted(edges):
        if a != b and (b, a) in edges:
            conflicts.append({
                "type": "reference-deadlock", "severity": "warn",
                "files": sorted({a, b}),
                "evidence": f"circular cross-file references between {a} and {b}",
            })

    for fa in file_analyses:
        rules = fa.get("rules", [])
        numbered = [r for r in rules if r["numbered"]]
        unnumbered = [r for r in rules if not r["numbered"]]
        if len(numbered) >= 2 and len(unnumbered) >= 2:
            conflicts.append({
                "type": "priority-ambiguity", "severity": "info",
                "files": [fa["path"]],
                "evidence": (f"{fa['path']} mixes {len(numbered)} numbered and "
                             f"{len(unnumbered)} unnumbered rules"),
            })

    tool_files = {}
    for file, line, text, numbered in all_rules:
        for tool in TOOL_RE.findall(text):
            tool_files.setdefault(tool, set()).add(file)
    for tool in sorted(tool_files):
        files = tool_files[tool]
        if len(files) < 2:
            continue
        required_any = optional_any = False
        for file in sorted(files):
            rules_for = [r for r in all_rules if r[0] == file and tool in r[2]]
            if any(any(m in r[2] for m in REQUIRE_MARKERS) for r in rules_for):
                required_any = True
            if any(re.search(r"\b(optional|may|might|can|if needed)\b", r[2]) for r in rules_for):
                optional_any = True
        if required_any and optional_any:
            conflicts.append({
                "type": "conflicting-scope", "severity": "warn",
                "files": sorted(files),
                "evidence": f"tool '{tool}' is required in one file and optional in another",
            })

    conflicts.sort(key=lambda c: (SEVERITY_ORDER[c["severity"]], c["type"], tuple(c["files"]), c["evidence"]))
    return conflicts
