# tests/test_governance_engine.py
import pytest
import asyncio
from pathlib import Path
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.config.loader import SandboxConfig
from harness.core.models import Action, GuardrailRule

@pytest.fixture
def engine(workspace_root):
    guardrails = GuardrailEngine(rules=[
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
        GuardrailRule(pattern=r"git\s+push", severity="approve", description="pushing"),
    ])
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py"]))
    hitl = HITLStateMachine(timeout_seconds=2)
    return GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

@pytest.mark.asyncio
async def test_blocks_dangerous_shell(engine):
    action = Action(type="run_shell", command="rm -rf /")
    decision = await engine.evaluate(action)
    assert decision.blocked is True
    assert decision.allowed is False

@pytest.mark.asyncio
async def test_blocks_path_traversal(engine):
    action = Action(type="read_file", path="../../etc/passwd")
    decision = await engine.evaluate(action)
    assert decision.blocked is True

@pytest.mark.asyncio
async def test_allows_safe_read(engine, workspace_root):
    (workspace_root / "foo.py").write_text("print('hi')")
    action = Action(type="read_file", path="foo.py")
    decision = await engine.evaluate(action)
    assert decision.allowed is True
    assert decision.blocked is False

@pytest.mark.asyncio
async def test_hitl_pause_and_approve(engine):
    action = Action(type="run_shell", command="git push origin main")
    task = asyncio.create_task(engine.evaluate(action))
    await asyncio.sleep(0.05)
    pending = engine.hitl.get_pending_requests()
    assert len(pending) == 1
    engine.hitl.resolve(pending[0].id, ApprovalState.APPROVED, "test")
    decision = await task
    assert decision.allowed is True
    assert decision.blocked is False

@pytest.mark.asyncio
async def test_hitl_denied(engine):
    action = Action(type="run_shell", command="git push origin main")
    task = asyncio.create_task(engine.evaluate(action))
    await asyncio.sleep(0.05)
    pending = engine.hitl.get_pending_requests()
    engine.hitl.resolve(pending[0].id, ApprovalState.DENIED, "test")
    decision = await task
    assert decision.blocked is True
    assert "not approved" in decision.reason.lower()

@pytest.mark.asyncio
async def test_non_shell_non_file_action_passes(engine):
    action = Action(type="task_complete")
    decision = await engine.evaluate(action)
    assert decision.allowed is True
