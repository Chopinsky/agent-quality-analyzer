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
