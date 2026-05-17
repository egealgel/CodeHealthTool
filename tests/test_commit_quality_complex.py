from pathlib import Path

from codehealth.analyzers import commit_quality
from codehealth.utils.git import parse_log


FIXTURE = Path(__file__).parent / "fixtures" / "commits_complex.txt"


def _load():
    return commit_quality.analyze(parse_log(FIXTURE.read_text()))


def _subjects_with_severity(report, severity):
    return {f.subject for f in report.findings if f.severity == severity}


def test_conventional_commits_pass():
    report = _load()
    clean = {
        "feat: add password reset endpoint with rate limiting",
        "fix(auth): correct JWT expiry handling for refresh tokens",
        "chore: bump dependencies to latest minor versions",
    }
    flagged = {f.subject for f in report.findings}
    assert clean.isdisjoint(flagged), f"conventional commits should be clean: {clean & flagged}"


def test_repeated_wip_flagged():
    report = _load()
    bads = _subjects_with_severity(report, "bad")
    assert "wip wip wip" in bads


def test_emoji_commit_not_flagged():
    report = _load()
    flagged = {f.subject for f in report.findings}
    assert "🐛 fix segfault in image resizer" not in flagged


def test_whitespace_only_treated_as_empty():
    report = _load()
    # the whitespace-only message becomes empty after strip; should still be flagged bad
    bads = _subjects_with_severity(report, "bad")
    assert "" in bads


def test_merge_and_revert_skipped():
    report = _load()
    flagged = {f.subject for f in report.findings}
    assert not any(s.startswith("Merge pull request") for s in flagged)
    assert not any(s.startswith("Revert ") for s in flagged)


def test_numeric_only_flagged():
    report = _load()
    warns = _subjects_with_severity(report, "warn")
    assert "1234567890" in warns


def test_non_imperative_caught():
    report = _load()
    warns = _subjects_with_severity(report, "warn")
    assert "Refactored the cache invalidation logic to avoid races" in warns
    assert "Fixing typo in readme" in warns


def test_good_descriptive_commit_clean():
    report = _load()
    flagged = {f.subject for f in report.findings}
    assert "Add comprehensive integration tests for payment flow" not in flagged
