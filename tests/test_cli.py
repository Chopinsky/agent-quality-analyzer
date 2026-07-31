import json
import subprocess

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


def test_analyze_empty_dir(tmp_path):
    assert main(["analyze", str(tmp_path)]) == 2


def test_analyze_single_file(tmp_path):
    f = tmp_path / "AGENTS.md"
    f.write_text("# Agent\n\n- one rule, stop when done.\n", encoding="utf-8")
    out = tmp_path / "f.json"
    assert main(["analyze", str(f), "--json", str(out)]) == 0
    contract = json.loads(out.read_text(encoding="utf-8"))
    assert contract["mode"] == "base"
    assert len(contract["files"]) == 1
    assert contract["files"][0]["path"] == "AGENTS.md"


def test_analyze_single_file_missing(tmp_path):
    assert main(["analyze", str(tmp_path / "nope.md")]) == 2


def test_analyze_single_file_diff_mode(tmp_path):
    f = tmp_path / "AGENTS.md"
    f.write_text("# Agent\n", encoding="utf-8")
    assert main(["analyze", str(f), "--mode", "diff"]) == 2


def test_analyze_diff_touched_only(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), check=True)
    (tmp_path / "AGENTS.md").write_text("# Agent\n\n- one rule, stop when done.\n", encoding="utf-8")
    skill = tmp_path / ".claude" / "skills" / "s1" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Skill\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=str(tmp_path), check=True)
    (tmp_path / "AGENTS.md").write_text(
        "# Agent\n\n- one rule, stop when done.\n- do not use the write tool\n", encoding="utf-8")
    out = tmp_path / "f.json"
    assert main(["analyze", str(tmp_path), "--mode", "diff", "--json", str(out)]) == 0
    contract = json.loads(out.read_text(encoding="utf-8"))
    assert [f["path"] for f in contract["files"]] == ["AGENTS.md"]
    assert [e["path"] for e in contract["diff"]["per_file"]] == ["AGENTS.md"]


def test_report_wrong_shape_findings(tmp_path):
    (tmp_path / "f.json").write_text("[1, 2, 3]", encoding="utf-8")
    assert main(["report", str(tmp_path / "f.json")]) == 2


def test_report_missing_scores(tmp_path):
    (tmp_path / "f.json").write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    assert main(["report", str(tmp_path / "f.json")]) == 2


def test_report_wrong_shape_llm(tmp_path):
    (tmp_path / "f.json").write_text(json.dumps({
        "schema_version": "1.0", "mode": "base", "target": str(tmp_path),
        "git": {"repo": False, "head": None, "base": None, "dirty": False},
        "files": [], "conflicts": [],
        "scores": {"d1": 100, "d2": 100, "d3": 100, "d4": 100, "d5": 100,
                   "structural": 100, "conflicts": 100, "overall": 100, "grade": "A"},
        "diff": None, "llm": None,
    }), encoding="utf-8")
    (tmp_path / "l.json").write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert main(["report", str(tmp_path / "f.json"), "--llm", str(tmp_path / "l.json")]) == 2
