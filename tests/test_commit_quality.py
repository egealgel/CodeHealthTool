from pathlib import Path

from codehealth.analyzers import commit_quality
from codehealth.utils.git import Commit, parse_log


FIXTURE = Path(__file__).parent / "fixtures" / "commits_sample.txt"


def load_fixture() -> list[Commit]:
    return parse_log(FIXTURE.read_text())


def test_parses_fixture_log():
    commits = load_fixture()
    assert len(commits) == 10
    assert commits[0].sha == "a1b2c3d4e5f6"
    assert commits[0].subject == "fix bug"


def test_flags_generic_messages():
    report = commit_quality.analyze(load_fixture())
    bad_subjects = {f.subject for f in report.findings if f.severity == "bad"}
    assert "fix bug" in bad_subjects
    assert "asdf" in bad_subjects
    assert "wip" in bad_subjects
    assert "stuff" in bad_subjects


def test_flags_too_short():
    report = commit_quality.analyze(load_fixture())
    too_short = [f for f in report.findings if f.rule == "too-short"]
    short_subjects = {f.subject for f in too_short}
    assert "t" in short_subjects
    assert "..." in short_subjects


def test_ignores_merge_commits():
    report = commit_quality.analyze(load_fixture())
    findings_for_merge = [f for f in report.findings
                          if f.subject.startswith("Merge branch")]
    assert findings_for_merge == []


def test_good_message_is_clean():
    report = commit_quality.analyze(load_fixture())
    good = "Add user authentication middleware with JWT validation"
    findings_for_good = [f for f in report.findings if f.subject == good]
    assert findings_for_good == []


def test_non_imperative_warn():
    report = commit_quality.analyze(load_fixture())
    warns = [f for f in report.findings
             if f.subject.startswith("Updated") and f.severity == "warn"]
    assert warns, "expected a warning for non-imperative 'Updated readme...'"


def test_score_computation():
    report = commit_quality.analyze(load_fixture())
    assert report.total == 10
    assert report.bad_count >= 5
    assert 0.0 < report.score <= 1.0
