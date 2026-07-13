# tests/test_mock_llm.py
import pytest
from harness.llm.mock_client import MockLLMClient
from harness.core.models import Message

@pytest.mark.asyncio
async def test_mock_returns_scripted_response():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    response = await client.complete([Message(role="user", content="do something")])
    assert response == '{"type": "task_complete"}'

@pytest.mark.asyncio
async def test_mock_returns_sequential_responses():
    client = MockLLMClient(scripted_responses=[
        '{"type": "run_shell", "command": "ls"}',
        '{"type": "task_complete"}',
    ])
    r1 = await client.complete([Message("user", "task")])
    r2 = await client.complete([Message("user", "task")])
    assert "ls" in r1
    assert "task_complete" in r2

@pytest.mark.asyncio
async def test_mock_raises_when_responses_exhausted():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    await client.complete([Message("user", "task")])
    with pytest.raises(IndexError):
        await client.complete([Message("user", "task")])

@pytest.mark.asyncio
async def test_mock_records_call_count():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'] * 3)
    await client.complete([Message("user", "t")])
    await client.complete([Message("user", "t")])
    assert client.call_count == 2

@pytest.mark.asyncio
async def test_mock_records_messages():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    msgs = [Message("system", "sys"), Message("user", "hello")]
    await client.complete(msgs)
    assert len(client.call_history) == 1
    assert client.call_history[0] == msgs
