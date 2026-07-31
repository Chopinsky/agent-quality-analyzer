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
