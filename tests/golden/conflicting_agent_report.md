# Agent Complexity Report

**Target:** `<TARGET>`
**Mode:** base
**Generated:** 2026-01-01
**Git:** repo: no | head: `-` | base: `-` | dirty: no

## Executive Summary

**Overall Score:** 95/100 — Grade A

**Top Findings:**

- `.claude/agents/helper.md:1` [warn] missing-edge-case-coverage: no error/fallback/retry keywords found
- `AGENTS.md:1` [warn] empty-section: section 'conflicting agent' is empty
- `AGENTS.md:1` [warn] missing-edge-case-coverage: no error/fallback/retry keywords found

## Scores

| Area | Score | Grade | Weight |
|---|---|---|---|
| Instruction Density & Length | 100 | A | 15% |
| Branching Factor | 100 | A | 15% |
| Tool & Constraint Coupling | 100 | A | 10% |
| Negative Constraints | 100 | A | 15% |
| Ambiguity / Entropy | 100 | A | 15% |
| Structural Lint | 94 | A | 20% |
| Conflict Detection | 60 | D | 10% |

## Key Metrics

| File | Tokens | Rules | Branching | Negatives | Neg. Ratio | Hedges | Tools | Entropy |
|---|---|---|---|---|---|---|---|---|
| `.claude/agents/helper.md` | 42 | 3 | 2 | 1 | 0.333 | 0 | 1 | 4.454 |
| `AGENTS.md` | 65 | 9 | 2 | 2 | 0.222 | 0 | 4 | 4.656 |

## Findings

### Error

_None._

### Warn

- `.claude/agents/helper.md:1` — missing-edge-case-coverage: no error/fallback/retry keywords found
- `AGENTS.md:1` — empty-section: section 'conflicting agent' is empty
- `AGENTS.md:1` — missing-edge-case-coverage: no error/fallback/retry keywords found

### Info

_None._

## Conflicts

- [error] contradictory-negation — files: `.claude/agents/helper.md`, `AGENTS.md` — 'never use the read tool for anything' (.claude/agents/helper.md:9) contradicts 'must use the read tool for all lookups' (AGENTS.md:6); shared terms: ['read', 'tool']
- [error] contradictory-negation — files: `AGENTS.md` — 'do not call the write tool at all' (AGENTS.md:8) contradicts 'always call the write tool first' (AGENTS.md:7); shared terms: ['call', 'tool', 'write']
- [error] contradictory-negation — files: `AGENTS.md` — 'do not call the write tool at all' (AGENTS.md:8) contradicts 'must use the read tool for all lookups' (AGENTS.md:6); shared terms: ['all', 'tool']
- [error] contradictory-negation — files: `AGENTS.md` — 'never use the read tool for anything' (AGENTS.md:5) contradicts 'must use the read tool for all lookups' (AGENTS.md:6); shared terms: ['read', 'tool']
- [warn] duplicate-rule — files: `.claude/agents/helper.md`, `AGENTS.md` — identical rule 'keep answers short and stop when done' at .claude/agents/helper.md:8 and AGENTS.md:9
- [warn] duplicate-rule — files: `.claude/agents/helper.md`, `AGENTS.md` — identical rule 'never use the read tool for anything' at .claude/agents/helper.md:9 and AGENTS.md:5

## Recommendations

- Fill or remove empty sections.
- Add error-handling guidance (failure, fallback, retry).

## Appendix: Per-File Metrics

```json
[
  {
    "path": ".claude/agents/helper.md",
    "metrics": {
      "tokens": 42,
      "rules": 3,
      "conditions": 1,
      "branching": 2,
      "tool_refs": 1,
      "cross_refs": 0,
      "negatives": 1,
      "negative_ratio": 0.333,
      "hedges": 0,
      "quantifiers": 0,
      "entropy": 4.454,
      "section_overlap": 0.0,
      "template_vars": 0,
      "sections": 1
    }
  },
  {
    "path": "AGENTS.md",
    "metrics": {
      "tokens": 65,
      "rules": 9,
      "conditions": 1,
      "branching": 2,
      "tool_refs": 4,
      "cross_refs": 0,
      "negatives": 2,
      "negative_ratio": 0.222,
      "hedges": 0,
      "quantifiers": 0,
      "entropy": 4.656,
      "section_overlap": 0.062,
      "template_vars": 0,
      "sections": 3
    }
  }
]
```
