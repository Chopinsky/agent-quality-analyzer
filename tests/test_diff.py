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
