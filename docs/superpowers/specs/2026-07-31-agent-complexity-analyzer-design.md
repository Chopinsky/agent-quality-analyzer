# Agent Quality Analyzer — Design Spec

**Date:** 2026-07-31
**Status:** Approved by user on 2026-07-31

## Goal

Build a skill + static Python scripts that analyze an agent's instruction files for complexity. The analysis runs in two modes: **base** (current state) and **diff** (before vs. after a git change). The final artifact is an installable skill/plugin for opencode and Claude Code, plus a CI-gate CLI. All analysis is deterministic (zero-LLM) except one clearly-bounded semantic layer performed by the skill agent itself.

## Reference sources

Best practices drawn from the "Zero-LLM & Static Prompt Linters" section:

- **hermes-labs/lintlang** — deterministic rules: missing stop conditions, ambiguous tool definitions, schema bloat, cyclomatic/structural complexity in multi-step agent directions.
- **NORTHTEKDevs/aiproof** — variable density, structural dependencies, edge-case coverage across instruction files.
- **HenrikBrehm/prompt-refiner-skill** — instruction bloat, conflicting constraints, over-engineering bugs causing context degradation / tool-use hallucination.
- **carbonbasednerd/prompt-analyzer** — contradiction, redundant-direction, and deadlock detection (we do this statically + via the skill agent's own semantic pass; no external model calls).
- **PromptEval / agenta / trulens / deepeval** — complexity-vs-quality framing; we borrow the dimension taxonomy only.

**Five complexity dimensions** (the Key Metrics list, all measured with deterministic lexical/structural rules — no embeddings):

1. Instruction Density & Length — token estimate, rule count, condition-to-token ratio
2. Branching Factor (Cyclomatic Complexity) — conditional-branch count
3. Tool & Constraint Coupling — tool references, schema bloat, cross-dependencies
4. Negative Constraint Ratio — "DO NOT" rule density
5. Ambiguity / Entropy — hedges, vague quantifiers, Shannon entropy, section-overlap

## Architecture

```
agent-quality-analyzer/
├── opencode.json                        # opencode plugin manifest → `opencode plugin add <repo>`
├── skill/agent-complexity-analyzer/     # self-contained skill dir → copy to ~/.claude/skills/ for Claude Code
│   ├── SKILL.md                         # frontmatter: name + description
│   └── scripts/                         # the Python package `aqa` (stdlib-only, single source of truth)
│       ├── __init__.py
│       ├── cli.py                       # entry point: analyze + report subcommands
│       ├── discovery.py                 # agent-file discovery
│       ├── static_analyzer.py           # 5-dimension metrics + structural lint rules
│       ├── conflict.py                  # deterministic conflict detection
│       ├── diff.py                      # git before/after comparison
│       ├── scores.py                    # penalty-based 0-100 scoring
│       └── report.py                    # deterministic MD renderer from JSON
├── pyproject.toml                       # package-dir maps to skill/.../scripts → `aqa` CLI
├── tests/
└── docs/
```

The skill directory is **self-contained** (scripts live inside it), so a Claude Code install — copying `skill/agent-complexity-analyzer/` to `~/.claude/skills/` — works with zero external setup. The opencode plugin manifest references the same directory; there is exactly one copy of the code.

## Components

### 1. discovery.py — file discovery

Deterministic, sorted path list. Patterns (relative to target dir):

- `AGENTS.md`, `CLAUDE.md` (any case)
- `.claude/agents/*.md`
- `.claude/skills/*/SKILL.md`
- `.cursor/rules/*.md`
- `.opencode/agent/*.md`
- `.opencode/skills/*/SKILL.md`
- `**/SKILL.md` (any depth)

Non-agent files (README.md, docs/, tests/, etc.) are ignored. Missing target dir → error exit code 2.

### 2. static_analyzer.py — five dimensions + structural lint

Per-file metrics (deterministic):

| Dimension | Rules |
|---|---|
| D1 Density & Length | token estimate = chars ÷ 4; rule count = bullet lines + heading count; condition-to-token ratio |
| D2 Branching | count of `if`/`when`/`unless`/`then`/`else`/`otherwise`; cyclomatic = 1 + branch count |
| D3 Coupling | tool-name references (`bash`, `read`, `edit`, `write`, `grep`, `glob`, `skill`, `task`, `webfetch`, `websearch`, `question`, …); frontmatter/tool-schema line count; cross-section references ("see Section", "per Rule", "above") |
| D4 Negatives | `do not`/`don't`/`never`/`must not`/`shall not`/`avoid`; ratio = negatives ÷ rule count (flag > 0.4) |
| D5 Ambiguity | hedges (`should`, `maybe`, `possibly`, `might`, `could`, `as needed`, `if applicable`, `whenever possible`); vague quantifiers (`some`, `various`, `several`, `multiple`, `a few`, `things`, `stuff`); Shannon entropy of word tokens; Jaccard vocab overlap between consecutive H2 sections (flag > 0.5) |

Structural lint rules (each emits a finding `{file, rule_id, severity, message, line}`):

- `missing-stop-conditions` (warn) — no `done`/`complete`/`exit`/`stop`/`finished`/`verify`/`verification` anywhere
- `unclosed-code-fence` (error) — odd count of ``` fence markers
- `unclosed-backtick` (warn) — odd count of inline-code backticks per line
- `duplicate-h1` (warn) — more than one `# heading` per file
- `empty-section` (warn) — heading with no content before next heading/EOF
- `template-variable-density` (warn) — `{{ ... }}` / `{% ... %}` count ÷ tokens above threshold
- `missing-edge-case-coverage` (warn) — no `error`/`failure`/`fallback`/`retry`/`edge case`/`exception` keywords
- `bloat` (warn) — file token estimate above threshold (default 1000 tokens)
- `missing-frontmatter` (warn) — agent/skill files lacking `name`/`description` frontmatter
- `oversized-frontmatter` (info) — frontmatter above 200 tokens

Severity levels: `info`, `warn`, `error`.

### 3. conflict.py — deterministic conflict detection

Emits `{type, files, severity, evidence}` entries:

- `duplicate-rule` (warn) — identical normalized bullet lines within or across files
- `near-duplicate-rule` (warn) — difflib ratio > 0.85 between rule lines
- `contradictory-negation` (error) — "do not X" vs "must X"/"always X" sharing keyword overlap
- `conflicting-scope` (warn) — same tool/domain referenced with different constraints
- `reference-deadlock` (warn) — section-reference cycle A→B→A
- `priority-ambiguity` (info) — numbered rules coexist with unnumbered rules on same topic

### 4. diff.py — before/after comparison (diff mode)

- Uses `git show <base>:<path>` for the base version (default base `HEAD`; `--base <ref>` overrides).
- Per file: metric deltas for all 5 dimensions, added/removed rule counts, added/removed findings by rule_id, changed-line count (from `git diff`).
- Regression risks (deterministic flags): density increase ≥ 20%, negative-constraint count increase, stop-condition removal, new conflict introduced, new error-severity findings, branching increase ≥ 20%.
- Not a git repo → `--diff` errors with exit code 3.

### 5. scores.py — penalty-based scoring

- Each area starts at 100; penalties subtracted per finding by severity (error 8, warn 4, info 1) and per dimension-ratio overage (documented step functions).
- Areas: D1 Density, D2 Branching, D3 Coupling, D4 Negatives, D5 Ambiguity, Structural, Conflicts.
- Weights: D1 15%, D2 15%, D3 10%, D4 15%, D5 15%, Structural 20%, Conflicts 10%.
- Overall = weighted mean, rounded to integer. Grades: A ≥ 90, B ≥ 80, C ≥ 65, D ≥ 50, F.
- 100% deterministic. LLM never contributes numeric scores.

### 6. report.py — deterministic MD renderer

Renders from the JSON contract. Fixed template, byte-deterministic (no timestamps inside the report body except a header line; stable ordering; no randomness). Sections:

1. Title + target/mode/git header
2. Executive summary — grade, overall score, top-3 findings by severity, LLM assessment paragraph (if present)
3. Score table — area, score, grade, weight
4. Key metrics table — the 5 dimensions per file
5. Findings by severity — `file:line` references
6. Conflicts — static + semantic (LLM) entries
7. Diff section (diff mode only) — per-file delta table, added/removed findings, regression risks
8. Recommendations — deterministic rule-based suggestions + LLM recommendations (if present)
9. Appendix — full per-file metrics dump

### 7. JSON contract (findings.json, schema v1)

```json
{
  "schema_version": "1.0",
  "mode": "base|diff",
  "target": "/abs/path",
  "git": {"repo": true, "head": "abc1234", "base": "HEAD", "dirty": false},
  "files": [{"path": "...", "metrics": {"d1_density": {...}, "d2_branching": {...}, "d3_coupling": {...}, "d4_negatives": {...}, "d5_ambiguity": {...}}, "findings": [{"rule_id": "...", "severity": "...", "message": "...", "line": 12}]}],
  "conflicts": [{"type": "...", "severity": "...", "files": ["..."], "evidence": "..."}],
  "scores": {"d1": 88, "d2": 90, "d3": 95, "d4": 72, "d5": 81, "structural": 76, "conflicts": 92, "overall": 84, "grade": "B"},
  "diff": {"per_file": [...], "regression_risks": [...]} | null,
  "llm": {"assessment": "...", "semantic_conflicts": [...], "recommendations": [...]} | null
}
```

The skill agent writes `llm.json` (same `llm` shape); `report.py` merges it at render time. The `llm` block is optional — report renders fine without it.

### 8. CLI

```
aqa analyze <target> [--mode base|diff] [--base <ref>] [--json <path>] [--report <path>]
aqa report <findings.json> [--llm <llm.json>] [--out <path>]
```

- `analyze` writes findings.json (default `findings.json` in cwd) and, with `--report`, also renders the MD.
- `report` renders MD from an existing findings.json, optionally merging `--llm llm.json`.
- Errors: exit 2 (bad target), exit 3 (diff requested but not a git repo / bad base ref), exit 1 (internal).

### 9. Skill (SKILL.md) workflow

Frontmatter: `name: agent-complexity-analyzer`, `description:` describing usage ("analyze agent instruction complexity, base or diff mode").

Skill agent procedure (written in SKILL.md):
1. Locate scripts dir (relative to SKILL.md — self-contained).
2. Run `python3 <scripts>/cli.py analyze <target> [--mode diff] --json <tmp>/findings.json`
3. Read findings.json.
4. LLM semantic pass: read the agent files; detect semantic contradictions/deadlocks the static tool missed; write `llm.json` (assessment + semantic_conflicts + recommendations).
5. Run `python3 <scripts>/cli.py report <tmp>/findings.json --llm <tmp>/llm.json --out <tmp>/report.md`
6. Output the report markdown verbatim (and tell the user where the .md was saved).

## Error handling

- Bad/missing target: CLI exit 2, message to stderr.
- `--diff` on non-git dir or unresolvable base ref: exit 3.
- Unreadable file (encoding errors): skipped with a warning finding; UTF-8 with `errors="replace"` never crashes.
- Scripts are stdlib-only Python 3.10+; no network access, no randomness → byte-deterministic output for identical input.

## Testing

pytest, stdlib-only (no pytest plugins requiring installs beyond pytest itself). Fixtures under `tests/fixtures/`:

- `clean_agent/` — well-formed AGENTS.md + skill file
- `bloated_agent/` — long file, many DO NOTs, hedges, unclosed code fence
- `conflicting_agent/` — duplicate rules + contradictory negations across two files
- `template_heavy/` — Jinja-style variables, no stop conditions

Tests:
- Metric correctness per fixture (assert exact numbers).
- Finding emission per rule (rule_id present, line numbers correct).
- Conflict detection cases.
- Score computation (known findings → exact score).
- Golden report test: byte-for-byte match of rendered MD for a fixed fixture set.
- Determinism test: two runs → identical bytes.
- Diff test: build temp git repo, commit, modify, assert deltas + regression risks.
- CLI e2e: exit codes, JSON output shape.

## Out of scope (YAGNI)

- No embeddings/LLM API calls in scripts.
- No template-engine (Jinja/Mustache) parsing — only density counting of `{{ }}`/`{% %}`.
- No network, no plugin dependencies beyond the Python stdlib.
- No runtime execution analysis, no agenta/trulens integration.
- No opencode-config customization; the repo is a standalone installable artifact.
