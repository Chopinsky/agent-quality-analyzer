import json
import shutil
from pathlib import Path

from aqa.cli import main
from aqa.discovery import discover_agent_files

FIXTURES = Path(__file__).parent / "fixtures"


def _analyze(tmp_path, fixture):
    shutil.copytree(FIXTURES / fixture, tmp_path / "agent")
    out = tmp_path / "f.json"
    assert main(["analyze", str(tmp_path / "agent"), "--json", str(out),
                 "--date", "2026-01-01"]) == 0
    return json.loads(out.read_text(encoding="utf-8"))


def test_discovery_on_fixtures(tmp_path):
    shutil.copytree(FIXTURES / "conflicting_agent", tmp_path / "agent")
    found = [str(p.relative_to(tmp_path / "agent")).replace("\\", "/")
             for p in discover_agent_files(tmp_path / "agent")]
    assert found == [".claude/agents/helper.md", "AGENTS.md"]


def test_clean_agent(tmp_path):
    contract = _analyze(tmp_path, "clean_agent")
    assert len(contract["files"]) == 2
    assert all(f["findings"] == [] for f in contract["files"])
    assert contract["scores"]["overall"] >= 90


def test_bloated_agent(tmp_path):
    contract = _analyze(tmp_path, "bloated_agent")
    rule_ids = {f["rule_id"] for f in contract["files"][0]["findings"]}
    assert {"bloat", "unclosed-code-fence", "duplicate-h1", "empty-section",
            "missing-stop-conditions", "template-variable-density",
            "missing-edge-case-coverage"} <= rule_ids
    assert contract["scores"]["d4"] < 100
    assert contract["scores"]["conflicts"] < 100


def test_conflicting_agent(tmp_path):
    contract = _analyze(tmp_path, "conflicting_agent")
    types = {c["type"] for c in contract["conflicts"]}
    assert {"duplicate-rule", "contradictory-negation"} <= types
    assert contract["scores"]["conflicts"] < 100


def test_template_heavy(tmp_path):
    contract = _analyze(tmp_path, "template_heavy")
    rule_ids = {f["rule_id"] for f in contract["files"][0]["findings"]}
    assert {"missing-frontmatter", "missing-stop-conditions",
            "template-variable-density"} <= rule_ids
    assert contract["scores"]["structural"] == 84
