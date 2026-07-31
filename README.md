# Agent Quality Analyzer

Deterministic, zero-LLM static analysis of agent instruction complexity. Measures
the five instruction-complexity dimensions (density & length, branching factor,
tool & constraint coupling, negative constraint ratio, ambiguity/entropy) plus
structural lint and conflict detection, in **base** mode (current state) and
**diff** mode (before/after a git change), and renders a fixed-format markdown
report. The skill agent adds only prose (assessment, semantic conflicts,
recommendations); every number is computed by scripts.

## Install

### opencode (skill)

No manifest or npm install is needed. opencode discovers skills by directory
convention only: a folder named after the skill that contains `SKILL.md`. Copy
the skill directory into a discovered location (global config dir):

```bash
cp -r skill/agent-complexity-analyzer ~/.config/opencode/skills/
```

PowerShell:

```powershell
Copy-Item -Recurse skill\agent-complexity-analyzer $env:USERPROFILE\.config\opencode\skills\
```

Or symlink (POSIX):

```bash
ln -s "$PWD/skill/agent-complexity-analyzer" ~/.config/opencode/skills/
```

### Claude Code (skill)

```bash
cp -r skill/agent-complexity-analyzer ~/.claude/skills/
```

Or symlink:

```bash
ln -s "$PWD/skill/agent-complexity-analyzer" ~/.claude/skills/
```

The skill directory is self-contained (scripts included); no Python packages to
install for skill use. Python 3.10+ is required.

### CLI (optional, for CI gates)

Without installing anything, run the shipped scripts directly:

```bash
cd skill/agent-complexity-analyzer/scripts
python -m aqa.cli analyze path/to/repo --mode diff --report report.md
```

Or install the package, which exposes the `aqa` command:

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
