from __future__ import annotations

import sys
from typing import TextIO

from codehealth.analyzers.commit_quality import CommitReport
from codehealth.analyzers.dead_code import DeadCodeReport


RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
DIM = "\033[2m"
RESET = "\033[0m"


def _color(stream: TextIO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def _c(text: str, code: str, stream: TextIO) -> str:
    return f"{code}{text}{RESET}" if _color(stream) else text


def render_dead_code(report: DeadCodeReport, stream: TextIO = sys.stdout) -> None:
    for d in report.dead:
        tag = _c("[DEAD]", RED, stream)
        stream.write(f"{tag} {d.file}:{d.line}  {d.kind} `{d.name}`\n")
    for d in report.maybe:
        tag = _c("[MAYBE]", YELLOW, stream)
        stream.write(f"{tag} {d.file}:{d.line}  {d.kind} `{d.name}` (decorated)\n")
    summary = f"{len(report.dead)} dead, {len(report.maybe)} maybe"
    if report.total == 0:
        summary = _c("no dead code found", GREEN, stream)
    stream.write(f"\n{summary}\n")


def render_commit_quality(report: CommitReport, stream: TextIO = sys.stdout) -> None:
    for f in report.findings:
        if f.severity == "bad":
            tag = _c("[BAD]", RED, stream)
        elif f.severity == "warn":
            tag = _c("[WARN]", YELLOW, stream)
        else:
            tag = _c("[INFO]", DIM, stream)
        short = f.sha[:7]
        stream.write(f'{tag} {short}  "{f.subject}"  — {f.message}\n')
    summary = (
        f"{report.bad_count} bad / {report.warn_count} warn / {report.total} commits  "
        f"(score: {report.score:.2f})"
    )
    if report.bad_count == 0 and report.warn_count == 0:
        summary = _c(summary, GREEN, stream)
    stream.write(f"\n{summary}\n")
