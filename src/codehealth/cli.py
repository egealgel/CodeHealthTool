from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codehealth.analyzers import commit_quality, dead_code
from codehealth.reporters import json_reporter, text
from codehealth.utils.git import GitError, read_log


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true",
                        help="emit JSON instead of text")
    common.add_argument("--fail-on-warn", action="store_true",
                        help="exit non-zero when warnings exist")

    p = argparse.ArgumentParser(
        prog="codehealth",
        description="Dead-code and commit-quality checks for Python projects",
        parents=[common],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("deadcode", parents=[common],
                        help="find never-called functions and classes")
    pd.add_argument("path", help="path to a Python file or package root")

    pc = sub.add_parser("commits", parents=[common],
                        help="analyze recent commit messages")
    pc.add_argument("repo_path", help="path to a git repository")
    pc.add_argument("-n", "--limit", type=int, default=100,
                    help="number of recent commits to check (default: 100)")

    pa = sub.add_parser("all", parents=[common], help="run both checks")
    pa.add_argument("path", help="path to a project (must be a git repo)")
    pa.add_argument("-n", "--limit", type=int, default=100)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "deadcode":
        return _run_deadcode(Path(args.path), args)
    if args.cmd == "commits":
        return _run_commits(Path(args.repo_path), args.limit, args)
    if args.cmd == "all":
        return _run_all(Path(args.path), args.limit, args)
    parser.error("unknown command")
    return 2


def _run_deadcode(path: Path, args) -> int:
    if not path.exists():
        print(f"path not found: {path}", file=sys.stderr)
        return 2
    report = dead_code.analyze(path)
    if args.json:
        print(json_reporter.render(json_reporter.dead_code_to_dict(report)))
    else:
        text.render_dead_code(report)
    return _exit_code(bad=len(report.dead), warn=len(report.maybe), args=args)


def _run_commits(repo: Path, limit: int, args) -> int:
    try:
        commits = read_log(repo, limit=limit)
    except GitError as e:
        print(f"git error: {e}", file=sys.stderr)
        return 3
    report = commit_quality.analyze(commits)
    if args.json:
        print(json_reporter.render(json_reporter.commit_quality_to_dict(report)))
    else:
        text.render_commit_quality(report)
    return _exit_code(bad=report.bad_count, warn=report.warn_count, args=args)


def _run_all(path: Path, limit: int, args) -> int:
    if not path.exists():
        print(f"path not found: {path}", file=sys.stderr)
        return 2

    dc = dead_code.analyze(path)
    try:
        commits = read_log(path, limit=limit)
        cq = commit_quality.analyze(commits)
    except GitError as e:
        print(f"git error: {e}", file=sys.stderr)
        return 3

    if args.json:
        payload = {
            "dead_code": json_reporter.dead_code_to_dict(dc),
            "commit_quality": json_reporter.commit_quality_to_dict(cq),
        }
        print(json_reporter.render(payload))
    else:
        print("== dead code ==")
        text.render_dead_code(dc)
        print("\n== commit quality ==")
        text.render_commit_quality(cq)

    bad = len(dc.dead) + cq.bad_count
    warn = len(dc.maybe) + cq.warn_count
    return _exit_code(bad=bad, warn=warn, args=args)


def _exit_code(*, bad: int, warn: int, args) -> int:
    if bad > 0:
        return 1
    if warn > 0 and args.fail_on_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
