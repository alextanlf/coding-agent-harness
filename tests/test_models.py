from harness.core.models import (
    Message, Action, ShellResult, Failure, TestFeedback,
    GuardrailRule, GuardrailDecision, SandboxDecision,
    ApprovalRequest, GovernanceDecision, RunResult,
)
from datetime import datetime

def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

def test_action_file_read():
    action = Action(type="read_file", path="src/foo.py")
    assert action.type == "read_file"
    assert action.path == "src/foo.py"
    assert action.command is None

def test_action_shell():
    action = Action(type="run_shell", command="ls -la")
    assert action.type == "run_shell"
    assert action.command == "ls -la"
    assert action.path is None

def test_shell_result():
    result = ShellResult(stdout="hello", stderr="", exit_code=0)
    assert result.exit_code == 0

def test_failure():
    f = Failure(name="test_bar", message="assert 1==2", file="test_foo.py", line=42)
    assert f.name == "test_bar"
    assert f.line == 42

def test_test_feedback():
    tf = TestFeedback(passed=False, failures=[Failure("t", "m", "f", 1)], raw_output="out")
    assert tf.passed is False
    assert len(tf.failures) == 1

def test_guardrail_rule():
    rule = GuardrailRule(pattern="rm -rf", severity="block", description="recursive delete")
    assert rule.severity == "block"

def test_guardrail_decision():
    d = GuardrailDecision(allowed=False, requires_approval=False, reason="blocked", rule=None)
    assert d.allowed is False

def test_sandbox_decision():
    d = SandboxDecision(allowed=True, reason="ok")
    assert d.allowed is True

def test_approval_request():
    req = ApprovalRequest(
        id="abc", action=Action(type="run_shell", command="git push"),
        reason="pushing", state="pending",
        created_at=datetime.now(), decided_at=None, decided_by=None,
    )
    assert req.state == "pending"

def test_governance_decision():
    d = GovernanceDecision(allowed=True, blocked=False, reason="")
    assert d.blocked is False

def test_run_result():
    r = RunResult(success=True, iterations=5, reason="task_complete")
    assert r.success is True
    assert r.iterations == 5
