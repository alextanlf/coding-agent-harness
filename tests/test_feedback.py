import pytest
from harness.feedback.engine import FeedbackEngine
from harness.core.models import ShellResult

@pytest.fixture
def engine():
    return FeedbackEngine(test_command="pytest", max_retries=3)

def test_parse_passed_tests(engine):
    output = ShellResult(stdout="1 passed in 0.5s", stderr="", exit_code=0)
    feedback = engine.parse_test_output(output)
    assert feedback.passed is True
    assert len(feedback.failures) == 0

def test_parse_failed_test(engine):
    output = ShellResult(
        stdout="",
        stderr="FAILED tests/test_foo.py::test_bar - assert 1 == 2\n1 failed in 0.3s",
        exit_code=1,
    )
    feedback = engine.parse_test_output(output)
    assert feedback.passed is False
    assert len(feedback.failures) == 1
    assert feedback.failures[0].name == "test_bar"
    assert "tests/test_foo.py" in feedback.failures[0].file

def test_parse_multiple_failures(engine):
    output = ShellResult(
        stdout="",
        stderr=(
            "FAILED tests/test_a.py::test_one - assert 1 == 2\n"
            "FAILED tests/test_b.py::test_two - KeyError: 'foo'\n"
            "2 failed in 0.5s"
        ),
        exit_code=1,
    )
    feedback = engine.parse_test_output(output)
    assert feedback.passed is False
    assert len(feedback.failures) == 2
    assert feedback.failures[0].name == "test_one"
    assert feedback.failures[1].name == "test_two"

def test_inject_passed_feedback(engine):
    from harness.core.models import TestFeedback
    feedback = TestFeedback(passed=True, failures=[], raw_output="")
    msg = engine.inject(feedback)
    assert "passed" in msg.content.lower()

def test_inject_failed_feedback(engine):
    from harness.core.models import TestFeedback, Failure
    feedback = TestFeedback(
        passed=False,
        failures=[Failure(name="test_bar", message="assert 1==2", file="test_foo.py", line=42)],
        raw_output="",
    )
    msg = engine.inject(feedback)
    assert "test_bar" in msg.content
    assert "assert 1==2" in msg.content
    assert "Fix" in msg.content

def test_truncates_raw_output(engine):
    long_output = "x" * 5000
    output = ShellResult(stdout=long_output, stderr="", exit_code=1)
    feedback = engine.parse_test_output(output)
    assert len(feedback.raw_output) <= 2000
