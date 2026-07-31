import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .conflict import detect_conflicts
from .diff import DiffError, diff_analysis, git_info
from .discovery import discover_agent_files
from .report import merge_llm, render_report
from .scores import compute_scores
from .static_analyzer import analyze_file

SCHEMA_VERSION = "1.0"


def cmd_analyze(args):
    target = Path(args.target)
    if not target.is_dir():
        print(f"error: target is not a directory: {args.target}", file=sys.stderr)
        return 2
    try:
        files = discover_agent_files(target)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rels = [str(p.relative_to(target)).replace("\\", "/") for p in files]
    file_analyses = [analyze_file(p, rel) for p, rel in zip(files, rels)]
    conflicts = detect_conflicts(file_analyses)
    scores = compute_scores(file_analyses, conflicts)
    git = git_info(target)
    diff = None
    if args.mode == "diff":
        try:
            diff = diff_analysis(target, args.base)
        except DiffError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        git["base"] = args.base
    else:
        git["base"] = None
    contract = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "target": str(target.resolve()),
        "git": git,
        "files": file_analyses,
        "conflicts": conflicts,
        "scores": scores,
        "diff": diff,
        "llm": None,
    }
    Path(args.json).write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"analyzed {len(file_analyses)} file(s) in {args.mode} mode")
    print(f"overall score: {scores['overall']}/100 ({scores['grade']})")
    print(f"findings written to: {args.json}")
    if args.report:
        out = render_report(contract, args.date or date.today().isoformat())
        Path(args.report).write_text(out, encoding="utf-8")
        print(f"report written to: {args.report}")
    return 0


def cmd_report(args):
    try:
        contract = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read findings JSON: {exc}", file=sys.stderr)
        return 2
    if args.llm:
        try:
            llm = json.loads(Path(args.llm).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read LLM JSON: {exc}", file=sys.stderr)
            return 2
        contract = merge_llm(contract, llm)
    out = render_report(contract, args.date or date.today().isoformat())
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"report written to: {args.out}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aqa",
                                     description="Static agent instruction complexity analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="analyze an agent directory")
    p_analyze.add_argument("target", help="directory containing agent instruction files")
    p_analyze.add_argument("--mode", choices=("base", "diff"), default="base")
    p_analyze.add_argument("--base", default="HEAD", help="git ref to compare against (diff mode)")
    p_analyze.add_argument("--json", default="findings.json")
    p_analyze.add_argument("--report", default=None, help="also render a report to this path")
    p_analyze.add_argument("--date", default=None, help="YYYY-MM-DD override (deterministic tests)")

    p_report = sub.add_parser("report", help="render a report from findings JSON")
    p_report.add_argument("findings", help="path to findings.json")
    p_report.add_argument("--llm", default=None, help="path to llm.json (skill agent semantic findings)")
    p_report.add_argument("--out", default="report.md")
    p_report.add_argument("--date", default=None, help="YYYY-MM-DD override (deterministic tests)")

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return cmd_analyze(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
