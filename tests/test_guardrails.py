# tests/test_guardrails.py
import pytest
from harness.governance.guardrails import GuardrailEngine
from harness.core.models import Action, GuardrailRule

@pytest.fixture
def engine():
    rules = [
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
        GuardrailRule(pattern=r"sudo", severity="block", description="sudo not allowed"),
        GuardrailRule(pattern=r"git\s+push", severity="approve", description="pushing to remote"),
        GuardrailRule(pattern=r"pip\s+install", severity="approve", description="installing packages"),
    ]
    return GuardrailEngine(rules=rules)

def test_blocks_rm_rf(engine):
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "recursive delete" in decision.reason

def test_blocks_sudo(engine):
    action = Action(type="run_shell", command="sudo apt-get update")
    decision = engine.evaluate(action)
    assert decision.allowed is False

def test_requires_approval_for_git_push(engine):
    action = Action(type="run_shell", command="git push origin main")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "pushing to remote" in decision.reason

def test_allows_safe_command(engine):
    action = Action(type="run_shell", command="ls -la")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is False

def test_non_shell_action_passes_through(engine):
    action = Action(type="read_file", path="src/foo.py")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is False

def test_empty_rules_allows_all():
    engine = GuardrailEngine(rules=[])
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.allowed is True

def test_multiple_block_rules_first_match_wins():
    rules = [
        GuardrailRule(pattern=r"rm", severity="approve", description="any rm"),
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="rm -rf"),
    ]
    engine = GuardrailEngine(rules=rules)
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.requires_approval is True
    assert decision.allowed is True
