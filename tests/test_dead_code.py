from pathlib import Path

from codehealth.analyzers import dead_code


FIXTURE = Path(__file__).parent / "fixtures" / "dead_code_sample"


def test_finds_unused_function_and_class():
    report = dead_code.analyze(FIXTURE)
    dead_names = {d.name for d in report.dead}
    assert "unused_helper" in dead_names
    assert "LegacyAdapter" in dead_names


def test_used_symbols_are_not_dead():
    report = dead_code.analyze(FIXTURE)
    dead_names = {d.name for d in report.dead}
    assert "used_function" not in dead_names
    assert "UsedClass" not in dead_names
    assert "method_called" not in dead_names


def test_dunder_methods_excluded():
    report = dead_code.analyze(FIXTURE)
    all_reported = {d.name for d in report.dead} | {d.name for d in report.maybe}
    assert "__init__" not in all_reported


def test_all_export_excluded():
    report = dead_code.analyze(FIXTURE)
    dead_names = {d.name for d in report.dead}
    assert "exported_dead_name" not in dead_names


def test_test_prefix_excluded():
    report = dead_code.analyze(FIXTURE)
    all_reported = {d.name for d in report.dead} | {d.name for d in report.maybe}
    assert "test_something" not in all_reported
    assert "TestStuff" not in all_reported
