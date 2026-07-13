# tests/test_loop_integration.py
import pytest
import asyncio
from pathlib import Path
from harness.core.loop import run_loop, EventEmitter
from harness.llm.mock_client import MockLLMClient
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import WriteFileTool, ReadFileTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.feedback.engine import FeedbackEngine
from harness.memory.store import MemoryStore
from harness.config.loader import HarnessConfig, SandboxConfig, GovernanceConfig
from harness.core.models import Action, GuardrailRule
from dataclasses import replace

@pytest.fixture
def setup_harness(workspace_root):
    guardrails = GuardrailEngine(rules=[
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
    ])
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py"]))
    hitl = HITLStateMachine(timeout_seconds=2)
    governance = GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

    reg = ToolRegistry()
    reg.register("write_file", WriteFileTool(sandbox))
    reg.register("read_file", ReadFileTool(sandbox))
    reg.register("run_shell", RunShellTool())

    feedback = FeedbackEngine(test_command="pytest", max_retries=3)
    memory = MemoryStore(system_prompt="You are a coding agent.")
    config = HarnessConfig(max_iterations=10, workspace_dir=str(workspace_root))

    return {
        "governance": governance,
        "tools": reg,
        "feedback": feedback,
        "memory": memory,
        "config": config,
        "sandbox": sandbox,
    }

@pytest.mark.asyncio
async def test_loop_completes_task(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "write_file", "path": "hello.py", "content": "print(\'hello\')"}',
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="write hello.py",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is True
    assert result.iterations == 2

@pytest.mark.asyncio
async def test_loop_blocks_dangerous_command(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "run_shell", "command": "rm -rf /"}',
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="delete everything",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is False
    assert llm.call_count == 2

@pytest.mark.asyncio
async def test_loop_max_iterations(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "read_file", "path": "foo.py"}',
    ] * 15)
    result = await run_loop(
        task="never complete",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=replace(h["config"], max_iterations=3),
    )
    assert result.success is False
    assert "max_iterations" in result.reason

@pytest.mark.asyncio
async def test_loop_handles_parse_error(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        "not valid json",
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="test",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is True
    assert llm.call_count == 2

@pytest.mark.asyncio
async def test_loop_emits_events(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "write_file", "path": "test.py", "content": "x = 1"}',
        '{"type": "task_complete"}',
    ])
    events = []

    class TestEmitter(EventEmitter):
        async def emit(self, event_type: str, data: dict):
            events.append({"type": event_type, "data": data})

    result = await run_loop(
        task="write test.py",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
        emitter=TestEmitter(),
    )
    assert result.success is True
    assert len(events) > 0
    assert any(e["type"] == "action" for e in events)
    assert any(e["type"] == "complete" for e in events)
