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
    if target.is_file():
        if args.mode != "base":
            print("error: diff mode requires a directory target", file=sys.stderr)
            return 2
        files = [target]
        rels = [target.name]
        git = git_info(target.parent)
    elif target.is_dir():
        try:
            files = discover_agent_files(target)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        rels = [str(p.relative_to(target)).replace("\\", "/") for p in files]
        git = git_info(target)
        if not files and args.mode != "diff":
            print("error: no agent instruction files found in target", file=sys.stderr)
            return 2
    else:
        print(f"error: target does not exist: {args.target}", file=sys.stderr)
        return 2
    file_analyses = [analyze_file(p, rel) for p, rel in zip(files, rels)]
    diff = None
    if args.mode == "diff":
        try:
            diff = diff_analysis(target, args.base)
        except DiffError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        git["base"] = args.base
        touched = {e["path"] for e in diff["per_file"]}
        file_analyses = [fa for fa in file_analyses if fa["path"] in touched]
    else:
        git["base"] = None
    conflicts = detect_conflicts(file_analyses)
    scores = compute_scores(file_analyses, conflicts)
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
    try:
        Path(args.json).write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write output JSON: {exc}", file=sys.stderr)
        return 2
    print(f"analyzed {len(file_analyses)} file(s) in {args.mode} mode")
    print(f"overall score: {scores['overall']}/100 ({scores['grade']})")
    print(f"findings written to: {args.json}")
    if args.report:
        out = render_report(contract, args.date or date.today().isoformat())
        try:
            Path(args.report).write_text(out, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write report: {exc}", file=sys.stderr)
            return 2
        print(f"report written to: {args.report}")
    return 0


def cmd_report(args):
    try:
        contract = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read findings JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(contract, dict) or not isinstance(contract.get("files"), list) \
            or not isinstance(contract.get("scores"), dict) \
            or "overall" not in contract["scores"] or "grade" not in contract["scores"]:
        print("error: findings JSON has invalid shape (expected files and scores)", file=sys.stderr)
        return 2
    if args.llm:
        try:
            llm = json.loads(Path(args.llm).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read LLM JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(llm, dict):
            print("error: LLM JSON must be an object with assessment/semantic_conflicts/recommendations",
                  file=sys.stderr)
            return 2
        contract = merge_llm(contract, llm)
    out = render_report(contract, args.date or date.today().isoformat())
    try:
        Path(args.out).write_text(out, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write report: {exc}", file=sys.stderr)
        return 2
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
