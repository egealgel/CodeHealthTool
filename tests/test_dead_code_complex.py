from pathlib import Path

from codehealth.analyzers import dead_code


FIXTURE = Path(__file__).parent / "fixtures" / "complex_sample"


def _names(defs):
    return {d.name for d in defs}


def test_visitor_dispatch_methods_excluded():
    report = dead_code.analyze(FIXTURE)
    all_reported = _names(report.dead) | _names(report.maybe)
    assert "visit_Call" not in all_reported
    assert "visit_FunctionDef" not in all_reported


def test_dataclass_decorator_is_safe():
    # GhostCat is @dataclass-decorated and never used → should be DEAD (not MAYBE)
    report = dead_code.analyze(FIXTURE)
    assert "GhostCat" in _names(report.dead)
    assert "GhostCat" not in _names(report.maybe)


def test_custom_decorator_marks_maybe():
    report = dead_code.analyze(FIXTURE)
    maybe = _names(report.maybe)
    assert "say_hello" in maybe
    assert "say_bye" in maybe


def test_truly_unused_is_dead():
    report = dead_code.analyze(FIXTURE)
    dead = _names(report.dead)
    assert "truly_dead" in dead
    assert "unused_factory" in dead


def test_string_annotation_is_a_reference():
    # StringAnnotated is only referenced via "StringAnnotated" string return annotation.
    report = dead_code.analyze(FIXTURE)
    all_reported = _names(report.dead) | _names(report.maybe)
    assert "StringAnnotated" not in all_reported


def test_regular_annotation_is_a_reference():
    report = dead_code.analyze(FIXTURE)
    all_reported = _names(report.dead) | _names(report.maybe)
    assert "OnlyUsedAsType" not in all_reported


def test_abstract_method_not_flagged_when_concrete_used():
    # Animal.speak is abstract; Dog.speak is concrete and called via d.speak().
    # Both share the name "speak" so neither should appear as dead.
    report = dead_code.analyze(FIXTURE)
    all_reported = _names(report.dead) | _names(report.maybe)
    assert "speak" not in all_reported


def test_live_entry_function_not_flagged():
    report = dead_code.analyze(FIXTURE)
    all_reported = _names(report.dead) | _names(report.maybe)
    assert "run" not in all_reported
