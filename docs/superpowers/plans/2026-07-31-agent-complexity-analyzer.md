# Agent Quality Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo that is simultaneously an installable skill/plugin (opencode + Claude Code) and a zero-LLM static analyzer CLI (`aqa`) producing deterministic complexity metrics, conflict analysis, base/diff modes, and a deterministic markdown report.

**Architecture:** One Python package `aqa` living inside the self-contained skill directory (`skill/agent-complexity-analyzer/scripts/`). Modules: `discovery` (find agent files), `static_analyzer` (5 complexity dimensions + structural lint), `conflict` (deterministic conflict detection), `scores` (penalty-based 0–100), `diff` (git before/after), `report` (deterministic MD renderer), `cli` (analyze/report subcommands). The skill agent runs the CLI, adds LLM-only semantic findings via `llm.json`, and the report script merges them.

**Tech Stack:** Python 3.10+ stdlib only, pytest, git, markdown.

## Global Constraints

- Python >= 3.10, stdlib only — no third-party imports in `aqa` package code.
- No network access, no randomness, no timestamps in output (dates only via explicit `--date`).
- All output ordering is sorted/deterministic; byte-identical output for identical input.
- Development shell is Windows PowerShell: run tests with `python -m pytest`, not `pytest`.
- Add `.gitattributes` with `* text=auto eol=lf` to avoid CRLF churn.
- No code comments in the codebase.
- The package source lives ONLY at `skill/agent-complexity-analyzer/scripts/aqa/` — never copy it elsewhere.
- Git commits after every green test run; message style `feat:` / `test:` / `docs:` / `chore:`.
- Exit codes: 0 success, 1 internal error, 2 bad target/args, 3 git-related failure (diff mode).

---

### Task 1: Repo scaffold

**Files:**
- Create: `.gitattributes`, `.gitignore`, `pyproject.toml`, `skill/agent-complexity-analyzer/scripts/aqa/__init__.py`, `tests/conftest.py`, `docs/superpowers/plans/.gitkeep` (not needed — plan already committed)

**Interfaces:**
- Consumes: nothing.
- Produces: importable package `aqa` (from `tests/` via conftest sys.path); pytest configured with `testpaths = ["tests"]`; packaging metadata for later `aqa` CLI install.

- [ ] **Step 1: Verify pytest is available**

Run: `python -m pytest --version`
Expected: version output. If "No module named pytest", run `python -m pip install pytest` first.

- [ ] **Step 2: Create `.gitattributes`**

```text
* text=auto eol=lf
```

- [ ] **Step 3: Create `.gitignore`**

```text
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
build/
dist/
.venv/
findings.json
report.md
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-quality-analyzer"
version = "0.1.0"
description = "Deterministic zero-LLM static analyzer for agent instruction complexity"
requires-python = ">=3.10"

[project.scripts]
aqa = "aqa.cli:main"

[tool.setuptools]
package-dir = {"" = "skill/agent-complexity-analyzer/scripts"}

[tool.setuptools.packages.find]
where = ["skill/agent-complexity-analyzer/scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Create the package `__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[0] / ".." / "skill" / "agent-complexity-analyzer" / "scripts"
sys.path.insert(0, str(SRC))
```

- [ ] **Step 7: Verify the import works**

Run: `python -c "import sys; sys.path.insert(0, 'skill/agent-complexity-analyzer/scripts'); import aqa; print(aqa.__version__)"`
Expected: `0.1.0`

- [ ] **Step 8: Commit**

```bash
git add .gitattributes .gitignore pyproject.toml skill tests
git commit -m "chore: scaffold repo, packaging, and test harness"
```

---

### Task 2: `discovery.py` — find agent instruction files

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/discovery.py`
- Test: `tests/test_discovery.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `discover_agent_files(target: Path) -> list[Path]` — absolute, sorted paths of agent instruction files; raises `ValueError` if target is not a directory. Patterns: `AGENTS.md`, `CLAUDE.md`, `agents.md`, `claude.md` at root; `*.md` under `.claude/agents`, `.claude/skills`, `.cursor/rules`, `.opencode/agent`, `.opencode/skills`; any `SKILL.md` at any depth. Excludes anything under a `.git` directory.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from aqa.discovery import discover_agent_files


def _tree(root):
    files = {
        "AGENTS.md": "# A\n",
        "CLAUDE.md": "# C\n",
        ".claude/agents/helper.md": "# H\n",
        ".claude/skills/helper/SKILL.md": "# S\n",
        ".cursor/rules/backend.md": "# R\n",
        ".opencode/agent/architect.md": "# O\n",
        ".opencode/skills/format/SKILL.md": "# F\n",
        "nested/deep/SKILL.md": "# D\n",
        "README.md": "# readme\n",
        "docs/guide.md": "# guide\n",
        ".git/AGENTS.md": "# git\n",
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_discover_all_patterns(tmp_path):
    root = _tree(tmp_path)
    found = [str(p.relative_to(root)).replace("\\", "/") for p in discover_agent_files(root)]
    assert found == sorted(found)
    assert "AGENTS.md" in found
    assert "CLAUDE.md" in found
    assert ".claude/agents/helper.md" in found
    assert ".claude/skills/helper/SKILL.md" in found
    assert ".cursor/rules/backend.md" in found
    assert ".opencode/agent/architect.md" in found
    assert ".opencode/skills/format/SKILL.md" in found
    assert "nested/deep/SKILL.md" in found
    assert "README.md" not in found
    assert "docs/guide.md" not in found
    assert ".git/AGENTS.md" not in found


def test_discover_empty_dir(tmp_path):
    assert discover_agent_files(tmp_path) == []


def test_discover_missing_target(tmp_path):
    with pytest.raises(ValueError):
        discover_agent_files(tmp_path / "missing")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.discovery'`

- [ ] **Step 3: Write the implementation**

```python
from pathlib import Path

ROOT_NAMES = ("AGENTS.md", "CLAUDE.md", "agents.md", "claude.md")
SKILL_SUBDIRS = (
    (".claude", "agents"),
    (".claude", "skills"),
    (".cursor", "rules"),
    (".opencode", "agent"),
    (".opencode", "skills"),
)


def discover_agent_files(target):
    target = Path(target)
    if not target.is_dir():
        raise ValueError(f"not a directory: {target}")
    found = []
    for name in ROOT_NAMES:
        path = target / name
        if path.is_file():
            found.append(path)
    for sub in SKILL_SUBDIRS:
        base = target.joinpath(*sub)
        if base.is_dir():
            found.extend(p for p in sorted(base.rglob("*.md")) if _not_git(p))
    found.extend(p for p in sorted(target.rglob("SKILL.md")) if _not_git(p))
    unique = {str(p): p for p in found}
    return sorted(unique.values(), key=lambda p: str(p.relative_to(target)).replace("\\", "/"))


def _not_git(path):
    return ".git" not in path.parts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/discovery.py tests/test_discovery.py
git commit -m "feat: discover agent instruction files deterministically"
```

---

### Task 3: `static_analyzer.py` — metrics part 1 (D1–D4)

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/static_analyzer.py`
- Test: `tests/test_static_analyzer.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `token_estimate(text: str) -> int` — `max(1, round(len(text) / 4))`
  - `normalize(s: str) -> str` — collapse whitespace, lowercase, strip punctuation
  - `extract_rules(text: str) -> list[dict]` — each `{"line": int, "text": str, "numbered": bool}`; bullets `- `, `* `, `+ `; numbered `1. ` / `1) `
  - `extract_headings(text: str) -> list[dict]` — each `{"level": int, "title": str, "line": int}`
  - `shannon_entropy(text: str) -> float` — word-token Shannon entropy, 3 decimals
  - `section_overlaps(text: str) -> float` — max Jaccard overlap of content words (stopwords removed) between consecutive H2 sections, 3 decimals
  - `analyze_text(text: str, rel_path: str) -> (dict, list)` — `(metrics, findings)`
  - `analyze_file(path: Path, rel_path: str) -> dict` — `{"path", "metrics", "findings", "rules", "headings"}`; unreadable file → warn finding, zeroed metrics
  - `is_agent_definition(rel_path: str) -> bool`
  - Metric keys: `tokens, rules, conditions, branching, tool_refs, cross_refs, negatives, negative_ratio, hedges, quantifiers, entropy, section_overlap, template_vars, sections`
  - Finding shape: `{"file": str, "rule_id": str, "severity": "info"|"warn"|"error", "message": str, "line": int}`

- [ ] **Step 1: Write the failing tests**

```python
from aqa.static_analyzer import (
    analyze_text,
    extract_rules,
    section_overlaps,
    shannon_entropy,
    token_estimate,
)

SIMPLE = """# H

- first rule
- second rule
1. third rule
plain text
"""


def test_token_estimate():
    assert token_estimate("a" * 100) == 25
    assert token_estimate("") == 1


def test_extract_rules():
    rules = extract_rules(SIMPLE)
    assert [(r["line"], r["text"], r["numbered"]) for r in rules] == [
        (3, "first rule", False),
        (4, "second rule", False),
        (5, "third rule", True),
    ]


def test_metrics_basic():
    text = (
        "# My Agent\n\n"
        "- When the user asks, use the bash tool, and stop when done.\n"
        "- If it fails, never retry silently; retry on error.\n"
        "- Then check the output and verify.\n"
    )
    metrics, findings = analyze_text(text, "AGENTS.md")
    assert metrics["rules"] == 4
    assert metrics["conditions"] == 3
    assert metrics["branching"] == 4
    assert metrics["tool_refs"] == 1
    assert metrics["negatives"] == 1
    assert metrics["negative_ratio"] == 0.25
    assert metrics["tokens"] == token_estimate(text)
    assert findings == []


def test_negative_ratio_zero_when_no_rules():
    metrics, _ = analyze_text("plain text without any rules\n", "AGENTS.md")
    assert metrics["rules"] == 0
    assert metrics["negative_ratio"] == 0.0


def test_shannon_entropy():
    assert shannon_entropy("a a b b") == 1.0
    assert shannon_entropy("") == 0.0


def test_section_overlap_high():
    text = (
        "## One\n\nuse the read tool and the grep tool often\n\n"
        "## Two\n\nuse the read tool and the grep tool often\n"
    )
    assert section_overlaps(text) > 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_static_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.static_analyzer'`

- [ ] **Step 3: Write the implementation**

```python
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
        "rules": len(rules),
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
    metrics["negative_ratio"] = round(metrics["negatives"] / max(len(rules), 1), 3)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_static_analyzer.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/static_analyzer.py tests/test_static_analyzer.py
git commit -m "feat: static metrics for instruction density, branching, coupling, negatives"
```

---

### Task 4: `static_analyzer.py` — structural lint findings

**Files:**
- Modify: `skill/agent-complexity-analyzer/scripts/aqa/static_analyzer.py` (no changes needed — `_lint_findings` already emits all rules)
- Test: `tests/test_lint_findings.py`

**Interfaces:**
- Consumes: `analyze_text(text, rel_path)` from Task 3.
- Produces: verified emission of rule_ids `bloat`, `unclosed-code-fence`, `unclosed-backtick`, `duplicate-h1`, `empty-section`, `missing-stop-conditions`, `template-variable-density`, `missing-edge-case-coverage`, `missing-frontmatter`, `oversized-frontmatter`, `unreadable-file`.

- [ ] **Step 1: Write the failing tests**

```python
from aqa.static_analyzer import analyze_text


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
```

- [ ] **Step 2: Run test to verify coverage**

Run: `python -m pytest tests/test_lint_findings.py -v`
Expected: PASS — `_lint_findings` was already implemented in Task 3; this task locks in explicit coverage for every rule_id. If any test fails, fix the rule logic in `_lint_findings` until all 8 pass (do not weaken the tests).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_lint_findings.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/static_analyzer.py tests/test_lint_findings.py
git commit -m "test: cover structural lint findings"
```

---

### Task 5: `conflict.py` — deterministic conflict detection

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/conflict.py`
- Test: `tests/test_conflict.py`

**Interfaces:**
- Consumes: `extract_rules`, `extract_headings`, `normalize` from `static_analyzer` (Task 3).
- Produces: `detect_conflicts(file_analyses: list[dict]) -> list[dict]` — each `{"type", "severity", "files": [rel paths sorted], "evidence": str}`; sorted by (severity error<warn<info, type, files, evidence). Types: `duplicate-rule` (warn), `near-duplicate-rule` (warn, difflib ratio > 0.85, skipped for identical texts), `contradictory-negation` (error), `conflicting-scope` (warn), `reference-deadlock` (warn), `priority-ambiguity` (info).
- Input dicts: `{"path": str, "metrics": dict, "findings": list, "rules": [{"line", "text", "numbered"}], "headings": [{"level", "title", "line"}]}`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_conflict.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.conflict'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_conflict.py -v`
Expected: PASS (9 tests). If `test_no_false_positive_on_distinct_rules` fails, check `SequenceMatcher` ratio of "format the output nicely" vs "keep the summary brief" — it must be below 0.85 (it is, ~0.4).

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/conflict.py tests/test_conflict.py
git commit -m "feat: deterministic conflict detection for agent rules"
```

---

### Task 6: `scores.py` — penalty-based 0–100 scoring

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/scores.py`
- Test: `tests/test_scores.py`

**Interfaces:**
- Consumes: `analyze_text` (Task 3) only in tests.
- Produces:
  - `WEIGHTS: dict` — `{"d1": 0.15, "d2": 0.15, "d3": 0.10, "d4": 0.15, "d5": 0.15, "structural": 0.20, "conflicts": 0.10}`
  - `grade_for(score: int) -> str` — A ≥ 90, B ≥ 80, C ≥ 65, D ≥ 50, else F
  - `compute_scores(file_analyses: list[dict], conflicts: list[dict]) -> dict` — keys `d1..d5, structural, conflicts, overall, grade`; area scores are rounded means of per-file scores; `conflicts` = 100 − sum(8/4/1 per error/warn/info); overall = weighted sum rounded.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scores.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.scores'`

- [ ] **Step 3: Write the implementation**

```python
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
```

Note: `compute_scores` returns dicts containing `overall` and `grade`, so the weights test above imports `WEIGHTS` directly — keep the import inside the test as shown.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scores.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/scores.py tests/test_scores.py
git commit -m "feat: deterministic penalty-based scoring"
```

---

### Task 7: `diff.py` — git before/after comparison

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/diff.py`
- Test: `tests/test_diff.py`

**Interfaces:**
- Consumes: `discover_agent_files` (Task 2), `analyze_text`, `extract_rules`, `extract_headings` (Task 3), `detect_conflicts` (Task 5).
- Produces:
  - `DiffError(Exception)`
  - `run_git(target: Path, args: list[str]) -> str` — raises `DiffError` on non-zero exit
  - `is_git_repo(target: Path) -> bool`
  - `git_info(target: Path) -> dict` — `{"repo": bool, "head": str|None, "dirty": bool}`
  - `base_content(target: Path, rel_path: str, base: str) -> str|None` — None when file absent at base
  - `line_counts(target: Path, rel_path: str, base: str) -> (int, int)` — (added, deleted)
  - `diff_analysis(target: Path, base: str = "HEAD") -> dict` — `{"per_file": [...], "regression_risks": [...]}`; per_file entries: `{"path", "base_present", "deltas": {metric: {"base", "current", "delta"}}, "added_rules", "removed_rules", "added_findings", "removed_findings", "lines_added", "lines_deleted"}`

- [ ] **Step 1: Write the failing tests**

```python
import subprocess

import pytest

from aqa.diff import DiffError, base_content, diff_analysis, git_info, is_git_repo, line_counts

V1 = "# Agent\n\n- one rule, stop when done, retry on error.\n"
V2 = (
    "# Agent\n\n"
    "- one rule, stop when done, retry on error.\n"
    "- do not use the read tool\n"
    "- do not use the write tool\n"
    "- do not use the edit tool\n"
    "- must use the read tool\n"
    "- keep answers short and stop when done\n"
    "- keep answers short and stop when done\n"
    "- keep answers short and stop when done\n"
    "- keep answers short and stop when done\n"
    "- keep answers short and stop when done\n"
)


def _init_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), check=True)


def _commit(path, message="commit"):
    subprocess.run(["git", "add", "-A"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=str(path), check=True)


def test_is_git_repo(tmp_path):
    assert not is_git_repo(tmp_path)
    _init_repo(tmp_path)
    assert is_git_repo(tmp_path)


def test_git_info(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    _commit(tmp_path)
    info = git_info(tmp_path)
    assert info["repo"] is True
    assert len(info["head"]) == 7
    assert info["dirty"] is False
    (tmp_path / "AGENTS.md").write_text(V2, encoding="utf-8")
    assert git_info(tmp_path)["dirty"] is True


def test_base_content(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    _commit(tmp_path)
    assert base_content(tmp_path, "AGENTS.md", "HEAD") == V1
    assert base_content(tmp_path, "nope.md", "HEAD") is None


def test_line_counts(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    _commit(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V2, encoding="utf-8")
    added, deleted = line_counts(tmp_path, "AGENTS.md", "HEAD")
    assert added > 0
    assert deleted == 0


def test_diff_analysis(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    _commit(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V2, encoding="utf-8")
    result = diff_analysis(tmp_path)
    entry = result["per_file"][0]
    assert entry["path"] == "AGENTS.md"
    assert entry["base_present"] is True
    assert entry["deltas"]["rules"]["delta"] == 9
    assert entry["deltas"]["negatives"]["delta"] == 3
    assert entry["lines_added"] > 0
    risks = result["regression_risks"]
    assert any("negative constraint" in r for r in risks)
    assert any("conflict count increased" in r for r in risks)


def test_diff_analysis_not_repo(tmp_path):
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    with pytest.raises(DiffError):
        diff_analysis(tmp_path)


def test_diff_analysis_bad_base(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(V1, encoding="utf-8")
    _commit(tmp_path)
    with pytest.raises(DiffError):
        diff_analysis(tmp_path, base="does-not-exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_diff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.diff'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_diff.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/diff.py tests/test_diff.py
git commit -m "feat: git diff analysis with regression risks"
```

---

### Task 8: `report.py` — deterministic markdown renderer

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `WEIGHTS`, `grade_for` from `scores` (Task 6).
- Produces:
  - `AREA_LABELS: dict`, `SEVERITY_ORDER: dict`, `SUGGESTIONS: dict`
  - `render_report(contract: dict, generated_date: str) -> str` — full deterministic MD
  - `merge_llm(contract: dict, llm: dict) -> dict` — returns new dict with `contract["llm"] = llm`
  - Contract shape consumed (produced by cli in Task 9): `{"schema_version", "mode", "target", "git": {"repo","head","base","dirty"}, "files": [{"path","metrics","findings","rules","headings"}], "conflicts": [{"type","severity","files","evidence"}], "scores": {"d1".."d5","structural","conflicts","overall","grade"}, "diff": {...}|None, "llm": {...}|None}`
  - `llm` block shape: `{"assessment": str, "semantic_conflicts": [str], "recommendations": [str]}`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.report'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_report.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/report.py tests/test_report.py
git commit -m "feat: deterministic markdown report renderer"
```

---

### Task 9: `cli.py` — analyze + report commands

**Files:**
- Create: `skill/agent-complexity-analyzer/scripts/aqa/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `discover_agent_files`, `analyze_file`, `detect_conflicts`, `compute_scores`, `git_info`, `diff_analysis`, `DiffError`, `render_report`, `merge_llm` (all previous tasks).
- Produces: `main(argv: list[str] | None = None) -> int` — CLI entry point. Subcommands:
  - `analyze <target> [--mode base|diff] [--base <ref>] [--json <path>] [--report <path>] [--date <YYYY-MM-DD>]`
  - `report <findings.json> [--llm <llm.json>] [--out <path>] [--date <YYYY-MM-DD>]`
  - Exit codes: 0 ok; 2 bad target or unreadable JSON; 3 git failure in diff mode.

- [ ] **Step 1: Write the failing tests**

```python
import json

from aqa.cli import main


def test_analyze_base(tmp_path):
    (tmp_path / "AGENTS.md").write_text(
        "# A\n\n- one rule, stop when done, retry on error.\n", encoding="utf-8")
    out_json = tmp_path / "f.json"
    out_report = tmp_path / "r.md"
    code = main(["analyze", str(tmp_path), "--json", str(out_json),
                 "--report", str(out_report), "--date", "2026-01-01"])
    assert code == 0
    contract = json.loads(out_json.read_text(encoding="utf-8"))
    assert contract["schema_version"] == "1.0"
    assert contract["mode"] == "base"
    assert len(contract["files"]) == 1
    assert contract["scores"]["overall"] == 100
    assert out_report.exists()


def test_analyze_bad_target(tmp_path):
    assert main(["analyze", str(tmp_path / "missing")]) == 2


def test_analyze_diff_not_repo(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# A\n", encoding="utf-8")
    assert main(["analyze", str(tmp_path), "--mode", "diff"]) == 3


def test_report_merge_llm(tmp_path):
    (tmp_path / "f.json").write_text(json.dumps({
        "schema_version": "1.0", "mode": "base", "target": str(tmp_path),
        "git": {"repo": False, "head": None, "base": None, "dirty": False},
        "files": [], "conflicts": [],
        "scores": {"d1": 100, "d2": 100, "d3": 100, "d4": 100, "d5": 100,
                   "structural": 100, "conflicts": 100, "overall": 100, "grade": "A"},
        "diff": None, "llm": None,
    }), encoding="utf-8")
    (tmp_path / "l.json").write_text(json.dumps({
        "assessment": "The agent is healthy overall.",
        "semantic_conflicts": ["Rule 2 and rule 9 disagree on approval flow."],
        "recommendations": ["Consider merging rules 4 and 5."],
    }), encoding="utf-8")
    out = tmp_path / "r.md"
    code = main(["report", str(tmp_path / "f.json"), "--llm", str(tmp_path / "l.json"),
                 "--out", str(out), "--date", "2026-01-01"])
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "The agent is healthy overall." in text
    assert "approval flow" in text
    assert "merging rules 4 and 5" in text


def test_report_bad_json(tmp_path):
    (tmp_path / "f.json").write_text("{not json", encoding="utf-8")
    assert main(["report", str(tmp_path / "f.json")]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aqa.cli'`

- [ ] **Step 3: Write the implementation**

```python
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .conflict import detect_conflicts
from .diff import DiffError, diff_analysis, git_info
from .discovery import discover_agent_files
from .report import merge_llm, render_report
from .scores import compute_scores
from .static_analyzer import analyze_file

SCHEMA_VERSION = "1.0"


def cmd_analyze(args):
    target = Path(args.target)
    if not target.is_dir():
        print(f"error: target is not a directory: {args.target}", file=sys.stderr)
        return 2
    try:
        files = discover_agent_files(target)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rels = [str(p.relative_to(target)).replace("\\", "/") for p in files]
    file_analyses = [analyze_file(p, rel) for p, rel in zip(files, rels)]
    conflicts = detect_conflicts(file_analyses)
    scores = compute_scores(file_analyses, conflicts)
    git = git_info(target)
    diff = None
    if args.mode == "diff":
        try:
            diff = diff_analysis(target, args.base)
        except DiffError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        git["base"] = args.base
    else:
        git["base"] = None
    contract = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "target": str(target.resolve()),
        "git": git,
        "files": file_analyses,
        "conflicts": conflicts,
        "scores": scores,
        "diff": diff,
        "llm": None,
    }
    Path(args.json).write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"analyzed {len(file_analyses)} file(s) in {args.mode} mode")
    print(f"overall score: {scores['overall']}/100 ({scores['grade']})")
    print(f"findings written to: {args.json}")
    if args.report:
        out = render_report(contract, args.date or date.today().isoformat())
        Path(args.report).write_text(out, encoding="utf-8")
        print(f"report written to: {args.report}")
    return 0


def cmd_report(args):
    try:
        contract = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read findings JSON: {exc}", file=sys.stderr)
        return 2
    if args.llm:
        try:
            llm = json.loads(Path(args.llm).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read LLM JSON: {exc}", file=sys.stderr)
            return 2
        contract = merge_llm(contract, llm)
    out = render_report(contract, args.date or date.today().isoformat())
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"report written to: {args.out}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aqa",
                                     description="Static agent instruction complexity analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="analyze an agent directory")
    p_analyze.add_argument("target", help="directory containing agent instruction files")
    p_analyze.add_argument("--mode", choices=("base", "diff"), default="base")
    p_analyze.add_argument("--base", default="HEAD", help="git ref to compare against (diff mode)")
    p_analyze.add_argument("--json", default="findings.json")
    p_analyze.add_argument("--report", default=None, help="also render a report to this path")
    p_analyze.add_argument("--date", default=None, help="YYYY-MM-DD override (deterministic tests)")

    p_report = sub.add_parser("report", help="render a report from findings JSON")
    p_report.add_argument("findings", help="path to findings.json")
    p_report.add_argument("--llm", default=None, help="path to llm.json (skill agent semantic findings)")
    p_report.add_argument("--out", default="report.md")
    p_report.add_argument("--date", default=None, help="YYYY-MM-DD override (deterministic tests)")

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return cmd_analyze(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (5 tests). If `test_analyze_base` overall is not 100, the fixture text must be exactly `"# A\n\n- one rule, stop when done, retry on error.\n"` (it trips no lint rules).

- [ ] **Step 5: Run the full suite so far**

Run: `python -m pytest -v`
Expected: PASS (all tests from Tasks 1–9)

- [ ] **Step 6: Commit**

```bash
git add skill/agent-complexity-analyzer/scripts/aqa/cli.py tests/test_cli.py
git commit -m "feat: aqa CLI with analyze and report commands"
```

---

### Task 10: Fixtures, golden report, determinism tests

**Files:**
- Create: `tests/fixtures/clean_agent/AGENTS.md`, `tests/fixtures/clean_agent/.claude/skills/helper/SKILL.md`, `tests/fixtures/bloated_agent/AGENTS.md`, `tests/fixtures/conflicting_agent/AGENTS.md`, `tests/fixtures/conflicting_agent/.claude/agents/helper.md`, `tests/fixtures/template_heavy/SKILL.md`, `tests/test_fixtures.py`, `tests/golden/conflicting_agent_report.md` (generated)
- Modify: `tests/test_report.py` (add golden + determinism tests)

**Interfaces:**
- Consumes: `main` from Task 9, `discover_agent_files` from Task 2.
- Produces: fixture corpus used by the skill agent examples and by golden/determinism tests.

- [ ] **Step 1: Create `tests/fixtures/clean_agent/AGENTS.md`**

```markdown
# Project Agent

## Scope

- Answer questions about the project codebase.
- Read files with the read tool and search with grep.
- On error, retry once, then stop and report the failure.

## When Finished

- Verify the answer against the code before responding.
- State what was verified and stop when done.
```

- [ ] **Step 2: Create `tests/fixtures/clean_agent/.claude/skills/helper/SKILL.md`**

```markdown
---
name: helper
description: Small helper skill used by the project agent.
---

# Helper

- Do one thing: format output.
- When finished, report the result and stop.
- If the input is invalid, error out and stop.
```

- [ ] **Step 3: Create `tests/fixtures/bloated_agent/AGENTS.md`** (40+ rules, many negatives, hedges, unclosed fence, duplicate H1, empty section, template vars, no stop words)

```markdown
# Bloated Agent

# Duplicate Title

## Goals

- do not use the read tool unless strictly required
- do not use the read tool unless strictly required
- must use the read tool for every task
- do not use the write tool without approval
- never call the edit tool directly
- must use the grep tool for all searches
- should use the bash tool when needed
- maybe try the glob tool sometimes
- do not forget to check the output
- do not skip the final check
- never assume the answer is correct
- do not trust the model's memory
- always double-check the results
- avoid using the web tool
- avoid long prompts
- avoid adding too many rules
- do not repeat the same instruction twice
- never contradict the system prompt
- must follow the system prompt exactly
- should keep every rule short
- could merge some rules together
- do not list every possible case
- never enumerate all tools
- avoid listing tools in detail
- do not describe tools at length
- never explain every tool
- avoid tool descriptions entirely
- do not write about tools at all
- never mention tools again
- do not use tools in examples
- avoid tool examples in text
- do not include tool usage samples
- never show tool call examples
- avoid sample tool invocations
- do not demonstrate tool usage
- never paste tool commands
- avoid command examples
- do not write shell commands
- never include code snippets

## Empty

## Output

- output the final result
- keep the summary brief
- finish with a short note

## Placeholders

- the model name is {{ model_name }}
- the session id is {{ session_id }}
- the task is {{ task_description }}
- the input is {{ user_input }}
- the context is {{ context_window }}
- the output format is {{ output_format }}
- the language is {{ output_language }}
- the tone is {{ output_tone }}
- the length is {{ output_length }}
- the audience is {{ target_audience }}
- the goal is {{ task_goal }}
- the constraint is {{ task_constraint }}

## Details

- every instruction should be evaluated as a separate unit of work that deserves its own careful consideration
- each rule maybe needs its own example to illustrate what correct behavior looks like in practice
- the entire set of instructions could be reorganized into several smaller files for better readability
- some users might prefer a shorter version with fewer rules and more general guidance
- various teams sometimes adopt different conventions across their repositories which creates friction
- multiple reviewers often disagree about whether a rule is too specific or too general in scope
- a few people generally want explicit permission lists while others prefer free-form guidance
- several projects end up with conflicting requirements that nobody notices until much later
- every system prompt should be written with the assumption that the reader is extremely patient
- the instruction set might grow over time as new capabilities are added to the underlying model
- each new capability usually brings its own constraints and its own set of edge cases to consider
- the whole document sometimes becomes harder to maintain as sections start to reference each other
- whenever possible the instructions should be self contained and not depend on external knowledge
- if applicable the rules should be written so that they apply to every future version of the product
- as needed the maintainer can add more detail but the core rules should stay stable across releases

```
Note: the trailing line must be exactly ```` ``` ```` (one unclosed fence) — write the last line as three backticks with nothing after.

- [ ] **Step 4: Create `tests/fixtures/conflicting_agent/AGENTS.md`**

```markdown
# Conflicting Agent

## Rules

- never use the read tool for anything
- must use the read tool for all lookups
- always call the write tool first
- do not call the write tool at all
- keep answers short and stop when done

## Done

- verify the answer and stop
```

- [ ] **Step 5: Create `tests/fixtures/conflicting_agent/.claude/agents/helper.md`**

```markdown
---
name: helper
description: Helper agent file used in conflict fixtures.
---

# Helper

- keep answers short and stop when done
- never use the read tool for anything
```

- [ ] **Step 6: Create `tests/fixtures/template_heavy/SKILL.md`**

```markdown
# Template Heavy Skill

- render the {{ template_name }} template with {{ max_iterations }} iterations
- use the {{ prompt_variant }} variant when the {{ user_query }} is short
- replace {{ placeholder }} with the actual value
- loop over {{ items }} and format {{ each_item }}
```

- [ ] **Step 7: Write the failing fixture tests (`tests/test_fixtures.py`)**

```python
import json
import shutil
from pathlib import Path

from aqa.cli import main
from aqa.discovery import discover_agent_files

FIXTURES = Path(__file__).parent / "fixtures"


def _analyze(tmp_path, fixture):
    shutil.copytree(FIXTURES / fixture, tmp_path / "agent")
    out = tmp_path / "f.json"
    assert main(["analyze", str(tmp_path / "agent"), "--json", str(out),
                 "--date", "2026-01-01"]) == 0
    return json.loads(out.read_text(encoding="utf-8"))


def test_discovery_on_fixtures(tmp_path):
    shutil.copytree(FIXTURES / "conflicting_agent", tmp_path / "agent")
    found = [str(p.relative_to(tmp_path / "agent")).replace("\\", "/")
             for p in discover_agent_files(tmp_path / "agent")]
    assert found == [".claude/agents/helper.md", "AGENTS.md"]


def test_clean_agent(tmp_path):
    contract = _analyze(tmp_path, "clean_agent")
    assert len(contract["files"]) == 2
    assert all(f["findings"] == [] for f in contract["files"])
    assert contract["scores"]["overall"] >= 90


def test_bloated_agent(tmp_path):
    contract = _analyze(tmp_path, "bloated_agent")
    rule_ids = {f["rule_id"] for f in contract["files"][0]["findings"]}
    assert {"bloat", "unclosed-code-fence", "duplicate-h1", "empty-section",
            "missing-stop-conditions", "template-variable-density",
            "missing-edge-case-coverage"} <= rule_ids
    assert contract["scores"]["d4"] < 100
    assert contract["scores"]["conflicts"] < 100


def test_conflicting_agent(tmp_path):
    contract = _analyze(tmp_path, "conflicting_agent")
    types = {c["type"] for c in contract["conflicts"]}
    assert {"duplicate-rule", "contradictory-negation"} <= types
    assert contract["scores"]["conflicts"] < 100


def test_template_heavy(tmp_path):
    contract = _analyze(tmp_path, "template_heavy")
    rule_ids = {f["rule_id"] for f in contract["files"][0]["findings"]}
    assert {"missing-frontmatter", "missing-stop-conditions",
            "template-variable-density"} <= rule_ids
    assert contract["scores"]["structural"] == 84
```

- [ ] **Step 8: Run fixture tests to verify they pass**

Run: `python -m pytest tests/test_fixtures.py -v`
Expected: PASS (5 tests). If `test_bloated_agent` fails on `bloat`, the file is too short — the fixture content above is ~4,600 chars (> 1,000 token estimate) by design; if the `template-variable-density` assertion fails, tokens are above `12 / 0.01 = 1200` — do not shrink the file below ~4,000 chars.

- [ ] **Step 9: Add golden + determinism tests (`tests/test_report.py` append)**

```python
import shutil
from pathlib import Path

from aqa.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"


def test_golden_conflicting_agent(tmp_path):
    shutil.copytree(FIXTURES / "conflicting_agent", tmp_path / "agent")
    out_json = tmp_path / "f.json"
    out_report = tmp_path / "r.md"
    assert main(["analyze", str(tmp_path / "agent"), "--json", str(out_json),
                 "--report", str(out_report), "--date", "2026-01-01"]) == 0
    actual = out_report.read_text(encoding="utf-8").replace(str(tmp_path / "agent"), "<TARGET>")
    assert actual == GOLDEN.read_text(encoding="utf-8")


def test_determinism(tmp_path):
    shutil.copytree(FIXTURES / "bloated_agent", tmp_path / "agent")
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    assert main(["analyze", str(tmp_path / "agent"), "--json", str(first),
                 "--date", "2026-01-01"]) == 0
    assert main(["analyze", str(tmp_path / "agent"), "--json", str(second),
                 "--date", "2026-01-01"]) == 0
    assert first.read_bytes() == second.read_bytes()
    r1 = tmp_path / "1.md"
    r2 = tmp_path / "2.md"
    assert main(["report", str(first), "--out", str(r1), "--date", "2026-01-01"]) == 0
    assert main(["report", str(second), "--out", str(r2), "--date", "2026-01-01"]) == 0
    assert r1.read_bytes() == r2.read_bytes()
```

- [ ] **Step 10: Run the new tests to verify they fail**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL — `test_golden_conflicting_agent` (golden file missing); `test_determinism` should PASS.

- [ ] **Step 11: Generate the golden file from a non-git temp copy**

The golden report must render with `repo: no | head: - | dirty: no` and a replaceable target path, so analyze a copy of the fixture placed in the temp dir (never the fixture dir itself — it sits inside this git repo, which would embed a head hash):

```powershell
$agent = "C:\Users\Halia\AppData\Local\Temp\opencode\golden-agent"
if (Test-Path $agent) { Remove-Item -Recurse -Force $agent }
Copy-Item -Recurse tests/fixtures/conflicting_agent $agent
python skill/agent-complexity-analyzer/scripts/aqa/cli.py analyze $agent --json C:\Users\Halia\AppData\Local\Temp\opencode\golden-f.json --report C:\Users\Halia\AppData\Local\Temp\opencode\golden-r.md --date 2026-01-01
```

Expected: exit 0. Then normalize the target path and write the golden file:

```powershell
$r = Get-Content -Raw C:\Users\Halia\AppData\Local\Temp\opencode\golden-r.md
$r = $r.Replace($agent, "<TARGET>")
Set-Content -NoNewline -Path tests/golden/conflicting_agent_report.md -Value $r
```

Verify the golden's Git line reads `repo: no | head: `-` | base: `-` | dirty: no` before committing.

- [ ] **Step 12: Run test to verify it passes**

Run: `python -m pytest tests/test_report.py -v`
Expected: PASS (7 tests)

- [ ] **Step 13: Full suite + commit**

Run: `python -m pytest -v`
Expected: all tests PASS. Then:

```bash
git add tests/fixtures tests/golden tests/test_fixtures.py tests/test_report.py
git commit -m "test: fixture corpus, golden report, and determinism checks"
```

---

### Task 11: SKILL.md — the orchestrating skill

**Files:**
- Create: `skill/agent-complexity-analyzer/SKILL.md`

**Interfaces:**
- Consumes: the `aqa` CLI (Task 9) at `<skill dir>/scripts/cli.py`.
- Produces: the skill definition that orchestrates analysis, LLM semantic pass, and report output; installable by opencode (plugin) and Claude Code (copy to `~/.claude/skills/`).

- [ ] **Step 1: Write `skill/agent-complexity-analyzer/SKILL.md`**

```markdown
---
name: agent-complexity-analyzer
description: Analyze the complexity of agent instruction files (AGENTS.md, CLAUDE.md, agent and skill definitions) with deterministic zero-LLM static analysis and a fixed markdown report. Use when the user asks to analyze an agent's instruction complexity, measure instruction bloat, check agent quality, compare an agent before/after changes (diff mode), or review rule conflicts. Triggers: "analyze this agent", "agent complexity", "check my AGENTS.md", "agent quality report", "did my agent get more complex", "instruction bloat", "conflicting rules in my agent".
---

# Agent Complexity Analyzer

Deterministic static analysis of agent instruction files. The Python scripts in
`scripts/` do all measurement and scoring; this skill only orchestrates, adds
semantic findings the scripts cannot see, and renders the final report.

## When to use

- The user wants to know how complex an agent's instruction files are.
- The user changed agent files and wants to know if complexity regressed.
- The user wants a report on instruction quality: density, branching, tool
  coupling, negative constraints, ambiguity, structural lint, and conflicts.

## Workflow

The scripts live in the same directory as this SKILL.md, under `scripts/`.
Resolve `<SKILL_DIR>` relative to this file. Use `python3` on Linux/macOS and
`python` on Windows.

1. Determine inputs. `TARGET` is the directory containing the agent files
   (defaults to the current working directory if the user gives no target).
   `MODE` is `base` (current state) or `diff` (before/after a git change;
   optional `--base <ref>` to compare against a specific ref, default `HEAD`).
   Run:

   ```
   python3 <SKILL_DIR>/scripts/cli.py analyze <TARGET> [--mode diff] [--base <ref>] --json <tmp>/findings.json
   ```

   Use a temp dir for output files (e.g. `$TMPDIR` or `C:\Users\<user>\AppData\Local\Temp`).

2. Read `findings.json`. It contains, per file, the five complexity dimensions
   (`tokens`, `rules`, `conditions`, `branching`, `tool_refs`, `cross_refs`,
   `negatives`, `negative_ratio`, `hedges`, `quantifiers`, `entropy`,
   `section_overlap`, `template_vars`, `sections`), structural lint findings,
   deterministic conflicts, scores (0-100 per area plus overall and grade), and
   (in diff mode) per-file deltas and regression risks.

3. Semantic pass (the only non-deterministic part — do this yourself, never in
   the scripts). Read the agent files and write `<tmp>/llm.json`:

   ```json
   {
     "assessment": "2-4 sentence high-level assessment of the agent's instruction quality",
     "semantic_conflicts": ["description of a semantic contradiction or deadlock the static tool missed, with file references"],
     "recommendations": ["concrete improvement suggestion"]
   }
   ```

   Constraints on this pass:
   - `assessment`, `semantic_conflicts`, and `recommendations` must be prose strings.
   - NEVER write or change any numbers, scores, grades, or metrics. Scores are
     computed deterministically by the scripts. Do not include scores in
     `assessment` prose; describe quality in words only.
   - Empty arrays are fine; omit keys you cannot fill honestly.

4. Render the report (deterministic template; the script merges your llm.json):

   ```
   python3 <SKILL_DIR>/scripts/cli.py report <tmp>/findings.json --llm <tmp>/llm.json --out <tmp>/report.md
   ```

5. Output the full content of `report.md` verbatim as the final message (it is
   the deliverable), and tell the user where the report was saved. Offer to copy
   it into their repo (e.g. `docs/agent-quality-report.md`) if they want.

## Notes

- If `analyze` exits 3 (diff mode on a non-git directory or bad base ref),
  explain the requirement and suggest `--mode base`.
- If `analyze` exits 2, the target is invalid; ask the user for a valid directory.
- The report is deterministic for identical inputs; only your `llm.json` prose
  varies between runs. Never claim a score you did not read from findings.json.
```

- [ ] **Step 2: Verify the skill directory is self-contained**

Run: `python -c "import sys; sys.path.insert(0, 'skill/agent-complexity-analyzer/scripts'); import aqa; print('ok')"`
Expected: `ok` — scripts importable from inside the skill dir with no external files.

- [ ] **Step 3: Commit**

```bash
git add skill/agent-complexity-analyzer/SKILL.md
git commit -m "docs: add agent-complexity-analyzer skill definition"
```

---

### Task 12: opencode plugin manifest, README, install verification

**Files:**
- Create: `opencode.json`, `README.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: installable plugin manifest (opencode) and install/usage docs (both tools).

- [ ] **Step 1: Write `opencode.json`**

```json
{
  "$schema": "https://opencode.ai/config.json",
  "name": "agent-complexity-analyzer",
  "version": "0.1.0",
  "description": "Zero-LLM static analyzer for agent instruction complexity with deterministic markdown reports (base/diff modes)",
  "skills": ["skill/agent-complexity-analyzer"]
}
```

- [ ] **Step 2: Verify the manifest against opencode docs**

Fetch: `https://opencode.ai/docs/plugins` (webfetch). Confirm the plugin manifest supports a `skills` array of directory paths relative to the plugin root. If the field name differs (e.g. `skill` singular), adjust `opencode.json` accordingly and note it in the commit.

- [ ] **Step 3: Write `README.md`**

```markdown
# Agent Quality Analyzer

Deterministic, zero-LLM static analysis of agent instruction complexity. Measures
the five instruction-complexity dimensions (density & length, branching factor,
tool & constraint coupling, negative constraint ratio, ambiguity/entropy) plus
structural lint and conflict detection, in **base** mode (current state) and
**diff** mode (before/after a git change), and renders a fixed-format markdown
report. The skill agent adds only prose (assessment, semantic conflicts,
recommendations); every number is computed by scripts.

## Install

### opencode (plugin)

```bash
opencode plugin add /path/to/agent-quality-analyzer
```

### Claude Code (skill)

```bash
cp -r skill/agent-complexity-analyzer ~/.claude/skills/
```

The skill directory is self-contained (scripts included); no Python packages to
install for skill use. Python 3.10+ is required.

### CLI (optional, for CI gates)

```bash
pip install .
aqa analyze path/to/repo --mode diff --report report.md
```

## Usage

```bash
aqa analyze <target> [--mode base|diff] [--base <ref>] [--json findings.json] [--report report.md]
aqa report findings.json [--llm llm.json] [--out report.md]
```

- `analyze` writes the JSON contract; `--report` also renders the markdown.
- `report` re-renders from JSON, optionally merging `--llm llm.json` (the
  skill agent's semantic findings: `assessment`, `semantic_conflicts`,
  `recommendations`).
- `--date YYYY-MM-DD` makes output byte-deterministic (used by tests).

Exit codes: 0 ok; 2 bad target/args/JSON; 3 diff-mode git failure.

## What it checks

| Area | Rules |
|---|---|
| D1 Density & Length | token estimate, rule count, bloat |
| D2 Branching Factor | if/when/unless/then/else count, branch density |
| D3 Tool Coupling | tool references, cross-section references, frontmatter bloat |
| D4 Negative Constraints | do-not/never/avoid ratio |
| D5 Ambiguity | hedges, vague quantifiers, entropy, section overlap |
| Structural | stop conditions, code fences, duplicate H1, empty sections, frontmatter, edge-case coverage, template variables |
| Conflicts | duplicate rules, near-duplicates, contradictory negations, scope conflicts, reference deadlocks, priority ambiguity |

## Development

```bash
python -m pytest
```

Determinism is tested by byte-comparing two full runs on the same fixture.
```

- [ ] **Step 4: Verify installability end-to-end**

Run: `python skill/agent-complexity-analyzer/scripts/aqa/cli.py analyze tests/fixtures/conflicting_agent --report C:\Users\Halia\AppData\Local\Temp\opencode\verify.md --date 2026-01-01`
Expected: exit 0; `verify.md` exists and contains `# Agent Complexity Report`.

- [ ] **Step 5: Commit**

```bash
git add opencode.json README.md
git commit -m "feat: opencode plugin manifest and README"
```

---

### Task 13: Final verification

**Files:** none new.

- [ ] **Step 1: Full test suite**

Run: `python -m pytest -v`
Expected: all tests PASS.

- [ ] **Step 2: Sanity CLI runs**

Run: `python skill/agent-complexity-analyzer/scripts/aqa/cli.py analyze tests/fixtures/bloated_agent --date 2026-01-01`
Expected: exit 0, `overall score: <X> (D or F)` — the bloated agent must score worse than clean.
Run: `python skill/agent-complexity-analyzer/scripts/aqa/cli.py analyze tests/fixtures/clean_agent --date 2026-01-01`
Expected: exit 0, `overall score: 100 (A)`.

- [ ] **Step 3: Verify git history is clean**

Run: `git status`
Expected: working tree clean.

- [ ] **Step 4: Final commit if anything changed**

```bash
git add -A
git commit -m "chore: final verification fixes"
```
(Only run if Step 3 shows changes.)

---

## Self-Review Notes (resolved during planning)

- **Spec coverage:** all spec sections map to tasks: discovery (T2), five dimensions + structural lint (T3/T4), static conflicts (T5), scoring with documented step penalties (T6), diff + regression risks (T7), deterministic report + LLM merge (T8), CLI + exit codes (T9), fixtures/golden/determinism (T10), skill workflow (T11), plugin manifest + docs (T12), verification (T13).
- **Placeholders:** none; every step has full code or an exact command.
- **Type consistency:** `analyze_text` returns `(metrics, findings)` everywhere; file analyses always carry `{"path", "metrics", "findings", "rules", "headings"}`; contract keys match between `cli.py` (producer), `report.py` (consumer), and `SKILL.md` (documentation); `diff` entries use `deltas` with `{base, current, delta}` consistently.
- **Known deviations from spec (intentional, documented):** fixture tests assert relations/rule-id presence instead of hand-computed exact scores (golden test locks exact bytes instead); a `--date` flag exists so byte-determinism is testable.
