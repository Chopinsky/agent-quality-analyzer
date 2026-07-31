# Agent Quality Analyzer

A skill that measures how complex your agent instruction files really are —
`AGENTS.md`, `CLAUDE.md`, agent and skill definitions. It runs a **deterministic,
zero-LLM static analysis** (5 complexity dimensions + structural lint +
conflict detection), scores the result 0–100 with a letter grade, and renders a
fixed-format report. Every number is computed by scripts; the skill agent only
adds prose (assessment, recommendations, semantic conflicts).

Run it in **base mode** on current files, or **diff mode** to check whether an
agent's complexity regressed after a change.

## Requirements

- macOS or Linux (Windows works too, see [Windows notes](#windows))
- Python 3.10+ (`python3 --version` — on macOS, `brew install python` if missing)
- Claude Code and/or opencode, or just the CLI

## Install

### Claude Code — marketplace (recommended)

In a Claude Code session, run:

```
/plugin marketplace add Chopinsky/agent-quality-analyzer
/plugin install agent-quality-analyzer@agent-quality-analyzer
/reload-plugins
```

Or from Claude Desktop: **Customize → Skills → + → paste
`Chopinsky/agent-quality-analyzer` → Sync**.

### Claude Code — manual (any install)

The skill is just a folder. Clone and symlink it into your personal skills
directory so it's available in every project:

```bash
git clone https://github.com/Chopinsky/agent-quality-analyzer.git
mkdir -p ~/.claude/skills
ln -s "$PWD/agent-quality-analyzer/skills/agent-complexity-analyzer" ~/.claude/skills/
```

Prefer copying instead of symlinking? Replace the last line with:

```bash
cp -R skills/agent-complexity-analyzer ~/.claude/skills/
```

**Project-scoped**: drop the same folder into `.claude/skills/` inside the
project repo and commit it, so the whole team gets it.

### opencode

opencode discovers skills by directory convention. Symlink (or copy) the skill
into the global skills directory:

```bash
git clone https://github.com/Chopinsky/agent-quality-analyzer.git
mkdir -p ~/.config/opencode/skills
ln -s "$PWD/agent-quality-analyzer/skills/agent-complexity-analyzer" ~/.config/opencode/skills/
```

**Project-scoped**: use `.opencode/skills/` instead.

### Verify it's installed

Start a new session and ask:

> Analyze the complexity of my agent instructions.

or, from a repo containing an `AGENTS.md`, run the CLI directly:

```bash
cd skills/agent-complexity-analyzer/scripts
python3 -m aqa.cli analyze path/to/your/repo
```

### Windows

```powershell
Copy-Item -Recurse skills\agent-complexity-analyzer "$env:USERPROFILE\.claude\skills\"
# or for opencode:
Copy-Item -Recurse skills\agent-complexity-analyzer "$env:USERPROFILE\.config\opencode\skills\"
```

Use `python` instead of `python3`.

## Usage

The skill is model-invoked: once installed, just ask for an analysis. Behind
the scenes it runs a two-phase workflow:

1. `analyze` — scripts compute metrics, findings, conflicts, scores and emit a
   JSON contract.
2. `report` — the skill agent adds prose via `llm.json` (assessment, semantic
   conflicts, recommendations), then the script renders the final markdown.

### CLI (for CI gates)

```bash
# from the skill's scripts dir, or after: pip install .
python3 -m aqa.cli analyze <target> [--mode base|diff] [--base <ref>] [--json findings.json] [--report report.md]
python3 -m aqa.cli report findings.json [--llm llm.json] [--out report.md]
```

- `--date YYYY-MM-DD` makes output byte-deterministic.
- Exit codes: 0 ok; 2 bad target/args/JSON; 3 diff-mode git failure.

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
