from codehealth.analyzers import commit_quality
from codehealth.utils.git import Commit


def _check(subject: str):
    return commit_quality.analyze([Commit(sha="abc1234", subject=subject, author="x")])


def test_release_tag_short_form_skipped():
    r = _check("v2.34.2")
    assert r.findings == []


def test_release_tag_with_rc_skipped():
    r = _check("v1.0.0rc1")
    assert r.findings == []


def test_release_tag_no_v_prefix_skipped():
    r = _check("2.0.1")
    assert r.findings == []


def test_release_word_skipped():
    r = _check("Release v3.5.0")
    assert r.findings == []


def test_django_issue_close_not_flagged_non_imperative():
    msg = "Fixed #37062 -- Added preserve_request support to RedirectView."
    r = _check(msg)
    rules = {f.rule for f in r.findings}
    assert "non-imperative" not in rules


def test_closes_pattern_not_flagged_non_imperative():
    r = _check("Closes #1234 -- improved error messages")
    rules = {f.rule for f in r.findings}
    assert "non-imperative" not in rules


def test_non_imperative_still_flagged_when_not_issue_close():
    r = _check("Updated the README to add examples")
    rules = {f.rule for f in r.findings}
    assert "non-imperative" in rules


def test_pr_ref_does_not_trigger_non_letter_heavy():
    r = _check("Reland #178362 (#183489)")
    rules = {f.rule for f in r.findings}
    assert "non-letter-heavy" not in rules


def test_bracket_tag_does_not_trigger_non_letter_heavy():
    r = _check("[CD] Add CPython-3.15b1 (#182954)")
    rules = {f.rule for f in r.findings}
    assert "non-letter-heavy" not in rules


def test_conventional_prefix_stripped_for_non_letter():
    r = _check("DOC: fix typo in install guide (#65323)")
    rules = {f.rule for f in r.findings}
    assert "non-letter-heavy" not in rules


def test_actual_noisy_message_still_flagged():
    # No identifiable PR ref / tag pattern, just garbage punctuation.
    r = _check("!@#$%^&*()_+!@#")
    rules = {f.rule for f in r.findings}
    assert "non-letter-heavy" in rules


def test_actual_bad_commit_still_caught():
    r = _check("asdf")
    severities = {f.severity for f in r.findings}
    assert "bad" in severities
