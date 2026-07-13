import pytest
import asyncio
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.core.models import Action

@pytest.fixture
def sm():
    return HITLStateMachine(timeout_seconds=2)

@pytest.mark.asyncio
async def test_request_approval_returns_pending(sm):
    action = Action(type="run_shell", command="git push")
    task = asyncio.create_task(sm.request_approval(action, "pushing to remote"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    assert len(pending) == 1
    assert pending[0].state == ApprovalState.PENDING
    sm.resolve(pending[0].id, ApprovalState.APPROVED, "test_user")
    result = await task
    assert result.state == ApprovalState.APPROVED

@pytest.mark.asyncio
async def test_denial(sm):
    action = Action(type="run_shell", command="pip install evil")
    task = asyncio.create_task(sm.request_approval(action, "installing"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    sm.resolve(pending[0].id, ApprovalState.DENIED, "test_user")
    result = await task
    assert result.state == ApprovalState.DENIED

@pytest.mark.asyncio
async def test_timeout(sm):
    sm = HITLStateMachine(timeout_seconds=0.1)
    action = Action(type="run_shell", command="rm file")
    result = await sm.request_approval(action, "deleting")
    assert result.state == ApprovalState.TIMEOUT

@pytest.mark.asyncio
async def test_resolve_nonexistent_raises(sm):
    with pytest.raises(KeyError):
        sm.resolve("nonexistent-id", ApprovalState.APPROVED, "user")

@pytest.mark.asyncio
async def test_double_resolve_raises(sm):
    action = Action(type="run_shell", command="git push")
    task = asyncio.create_task(sm.request_approval(action, "push"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    sm.resolve(pending[0].id, ApprovalState.APPROVED, "user")
    await task
    with pytest.raises(KeyError):
        sm.resolve(pending[0].id, ApprovalState.DENIED, "user")

@pytest.mark.asyncio
async def test_get_pending_requests_empty(sm):
    assert sm.get_pending_requests() == []
