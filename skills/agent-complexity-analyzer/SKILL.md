---
name: agent-complexity-analyzer
description: "Analyze the complexity of agent instruction files (AGENTS.md, CLAUDE.md, agent and skill definitions) with deterministic zero-LLM static analysis and a fixed markdown report. Use when the user asks to analyze an agent's instruction complexity, measure instruction bloat, check agent quality, compare an agent before/after changes (diff mode), or review rule conflicts. Triggers: \"analyze this agent\", \"agent complexity\", \"check my AGENTS.md\", \"agent quality report\", \"did my agent get more complex\", \"instruction bloat\", \"conflicting rules in my agent\"."
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
Resolve `<SKILL_DIR>` relative to this file. Run the CLI as a module from the
scripts directory (`python3 -m aqa.cli` — the package uses relative imports, so
`cli.py` cannot be executed directly). Use `python3` on Linux/macOS and
`python` on Windows.

1. Determine inputs. `TARGET` is the required directory containing the agent
   files; it must be an absolute path, so resolve it first (e.g. with
   `realpath`/`pwd -P`) before changing directories.
   `MODE` is `base` (current state) or `diff` (before/after a git change;
   optional `--base <ref>` to compare against a specific ref, default `HEAD`).
   Run:

   ```
   cd <SKILL_DIR>/scripts
   python3 -m aqa.cli analyze <TARGET> [--mode diff] [--base <ref>] --json <tmp>/findings.json
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
   cd <SKILL_DIR>/scripts
   python3 -m aqa.cli report <tmp>/findings.json --llm <tmp>/llm.json --out <tmp>/report.md
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
