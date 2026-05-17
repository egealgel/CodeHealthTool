from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from codehealth.utils.git import Commit


BLACKLIST = {
    "fix", "fix bug", "fix bugs", "fixes", "fixed",
    "wip", "tmp", "temp", "test", "tests", "testing",
    "update", "updates", "updated",
    "asdf", "qwer", "foo", "bar", "baz", "stuff", "misc",
    "changes", "edit", "edits", "minor", "tweak", "tweaks",
    ".", "..", "...",
}

GENERIC_REGEX = re.compile(
    r"^(fix(es|ed)?|update[ds]?|change[ds]?|wip|tmp|temp|test(s|ing)?|stuff|misc)\b\s*\.?$",
    re.IGNORECASE,
)

MERGE_REGEX = re.compile(r"^merge\s+(branch|pull|remote-tracking)", re.IGNORECASE)
REVERT_REGEX = re.compile(r"^revert\s+", re.IGNORECASE)

# Release / version tag commits — intentionally short, skip linting.
RELEASE_TAG_REGEX = re.compile(
    r"^(release\s+)?v?\d+\.\d+(\.\d+)?([._\-]?(a|b|rc|alpha|beta|dev|post)\d*)?$",
    re.IGNORECASE,
)

# Issue-closing convention used by Django, Rails, etc.
# "Fixed #NNNN -- ...", "Closes #NNN ...", "Resolves GH-123 ..."
ISSUE_CLOSE_REGEX = re.compile(
    r"^(fix(ed|es)?|close[ds]?|resolve[ds]?)\s+(#|gh[-_]?)\d+",
    re.IGNORECASE,
)

# Things to strip before measuring "non-letter density":
#   trailing/inline PR refs   "(#1234)"  or "#1234"
#   leading bracketed tags    "[CD]", "[BUGFIX]"
#   conventional prefixes     "feat:", "fix(scope):", "DOC:"
_NOISE_PATTERNS = [
    re.compile(r"\(#\d+\)"),
    re.compile(r"(?<!\w)#\d+"),
    re.compile(r"\[[^\]]+\]"),
    re.compile(r"^[A-Za-z]+(\([^)]+\))?:\s*"),
]


@dataclass(frozen=True)
class Finding:
    sha: str
    subject: str
    severity: str  # "bad" | "warn" | "info"
    rule: str
    message: str


@dataclass
class CommitReport:
    total: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def bad_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "bad")

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warn")

    @property
    def score(self) -> float:
        if self.total == 0:
            return 0.0
        bad_shas = {f.sha for f in self.findings if f.severity == "bad"}
        return len(bad_shas) / self.total


def analyze(commits: Iterable[Commit]) -> CommitReport:
    commits = list(commits)
    findings: list[Finding] = []
    for c in commits:
        findings.extend(_check_commit(c))
    return CommitReport(total=len(commits), findings=findings)


def _check_commit(c: Commit) -> list[Finding]:
    msg = c.subject.strip()
    out: list[Finding] = []

    if MERGE_REGEX.match(msg) or REVERT_REGEX.match(msg):
        return out
    if RELEASE_TAG_REGEX.match(msg):
        return out

    lowered = msg.lower().rstrip(".!?")

    if len(msg) < 8:
        out.append(Finding(c.sha, msg, "bad", "too-short",
                           f"subject is only {len(msg)} chars"))

    if lowered in BLACKLIST:
        out.append(Finding(c.sha, msg, "bad", "blacklist",
                           "generic/meaningless commit message"))
    elif GENERIC_REGEX.match(msg):
        out.append(Finding(c.sha, msg, "bad", "generic",
                           "matches generic placeholder pattern"))
    elif _all_tokens_blacklisted(lowered):
        out.append(Finding(c.sha, msg, "bad", "all-tokens-generic",
                           "every word is a generic placeholder"))

    if msg and _is_single_repeated_char(msg):
        out.append(Finding(c.sha, msg, "bad", "repeated-char",
                           "message is a single repeated character"))

    words = [w for w in re.split(r"\s+", msg) if w]
    if len(words) == 1 and len(msg) >= 8 and not any(f.rule == "blacklist" for f in out):
        out.append(Finding(c.sha, msg, "warn", "single-word",
                           "single-word commit message"))

    normalized = _strip_noise(msg)
    if normalized:
        # version numbers (0.15.10) and identifiers count as content;
        # only formatting/punctuation noise should drive this rule
        non_content = sum(
            1 for ch in normalized
            if not ch.isalnum() and not ch.isspace()
        )
        if non_content / len(normalized) > 0.5:
            out.append(Finding(c.sha, msg, "warn", "non-letter-heavy",
                               "more than 50% non-letter characters"))

    if words and not ISSUE_CLOSE_REGEX.match(msg):
        first = words[0].lower()
        if first.endswith("ed") or first.endswith("ing"):
            if not any(f.severity == "bad" for f in out):
                out.append(Finding(c.sha, msg, "warn", "non-imperative",
                                   f"'{words[0]}' is not imperative mood"))

    return out


def _strip_noise(msg: str) -> str:
    out = msg
    for pat in _NOISE_PATTERNS:
        out = pat.sub("", out)
    return out.strip()


def _is_single_repeated_char(s: str) -> bool:
    stripped = s.replace(" ", "")
    return len(stripped) >= 2 and len(set(stripped)) == 1


def _all_tokens_blacklisted(lowered: str) -> bool:
    tokens = [t for t in re.split(r"\s+", lowered) if t]
    if len(tokens) < 2:
        return False
    return all(t in BLACKLIST for t in tokens)
