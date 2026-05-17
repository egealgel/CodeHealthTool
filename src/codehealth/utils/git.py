from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    author: str


def read_log(repo: Path, limit: int = 100) -> list[Commit]:
    repo = Path(repo)
    if not (repo / ".git").exists() and not _inside_git(repo):
        raise GitError(f"Not a git repository: {repo}")

    fmt = "%H%x09%s%x09%an"
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", f"-n{limit}", f"--format={fmt}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise GitError("git executable not found in PATH") from e
    except subprocess.CalledProcessError as e:
        raise GitError(f"git log failed: {e.stderr.strip()}") from e

    return parse_log(proc.stdout)


def parse_log(raw: str) -> list[Commit]:
    commits: list[Commit] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        sha, subject, author = parts
        commits.append(Commit(sha=sha, subject=subject, author=author))
    return commits


def _inside_git(path: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"
