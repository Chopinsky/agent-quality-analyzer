import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[0] / ".." / "skill" / "agent-complexity-analyzer" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

ENV = {**os.environ, "PYTHONPATH": str(SCRIPTS)}


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "aqa.cli", *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV)


def test_e2e_analyze_clean_agent(tmp_path):
    out_json = tmp_path / "f.json"
    out_report = tmp_path / "r.md"
    proc = run_cli("analyze", str(FIXTURES / "clean_agent"), "--json", str(out_json),
                   "--report", str(out_report), "--date", "2026-01-01")
    assert proc.returncode == 0
    contract = json.loads(out_json.read_text(encoding="utf-8"))
    assert contract["schema_version"] == "1.0"
    assert contract["mode"] == "base"
    assert contract["scores"]["overall"] == 100
    assert contract["git"]["repo"]
    assert len(contract["files"]) == 2
    text = out_report.read_text(encoding="utf-8")
    assert text.startswith("# Agent Complexity Report")
    assert "**Generated:** 2026-01-01" in text


def test_e2e_analyze_bloated_agent(tmp_path):
    out_json = tmp_path / "f.json"
    proc = run_cli("analyze", str(FIXTURES / "bloated_agent"), "--json", str(out_json),
                   "--date", "2026-01-01")
    assert proc.returncode == 0
    contract = json.loads(out_json.read_text(encoding="utf-8"))
    rule_ids = {f["rule_id"] for f in contract["files"][0]["findings"]}
    assert "bloat" in rule_ids
    assert "unclosed-code-fence" in rule_ids


def test_e2e_report_subcommand(tmp_path):
    findings = tmp_path / "f.json"
    assert run_cli("analyze", str(FIXTURES / "conflicting_agent"),
                   "--json", str(findings), "--date", "2026-01-01").returncode == 0
    out = tmp_path / "r.md"
    proc = run_cli("report", str(findings), "--out", str(out), "--date", "2026-01-01")
    assert proc.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "## Conflicts" in text
    assert "contradictory-negation" in text


def test_e2e_error_exit_codes(tmp_path):
    assert run_cli("analyze", str(tmp_path / "missing")).returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run_cli("report", str(bad)).returncode == 2
    (tmp_path / "AGENTS.md").write_text("# A\n", encoding="utf-8")
    assert run_cli("analyze", str(tmp_path), "--mode", "diff").returncode == 3
