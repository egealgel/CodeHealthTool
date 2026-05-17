from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from codehealth.analyzers.commit_quality import CommitReport
from codehealth.analyzers.dead_code import DeadCodeReport


def dead_code_to_dict(report: DeadCodeReport) -> dict[str, Any]:
    return {
        "dead": [asdict(d) for d in report.dead],
        "maybe": [asdict(d) for d in report.maybe],
        "total": report.total,
    }


def commit_quality_to_dict(report: CommitReport) -> dict[str, Any]:
    return {
        "total": report.total,
        "bad": report.bad_count,
        "warn": report.warn_count,
        "score": round(report.score, 4),
        "findings": [asdict(f) for f in report.findings],
    }


def render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
