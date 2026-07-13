import pytest
from harness.memory.store import MemoryStore
from harness.core.models import Message, Action, ShellResult

def test_empty_memory_returns_system_and_task():
    store = MemoryStore(system_prompt="You are a coding agent.")
    messages = store.build_context("Write a hello world function")
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content == "You are a coding agent."
    assert messages[1].role == "user"
    assert "hello world" in messages[1].content

def test_record_and_retrieve():
    store = MemoryStore(system_prompt="sys")
    action = Action(type="write_file", path="foo.py", content="print('hi')")
    result = ShellResult(stdout="", stderr="", exit_code=0)
    store.record(action, result)
    messages = store.build_context("task")
    assert len(messages) >= 3

def test_last_n_actions_kept():
    store = MemoryStore(system_prompt="sys", max_context_actions=3)
    for i in range(10):
        action = Action(type="write_file", path=f"f{i}.py", content="x")
        store.record(action, ShellResult("", "", 0))
    messages = store.build_context("task")
    action_msgs = [m for m in messages if m.role == "assistant"]
    assert len(action_msgs) <= 3

def test_record_appends_assistant_and_user_messages():
    store = MemoryStore(system_prompt="sys")
    action = Action(type="run_shell", command="ls")
    result = ShellResult(stdout="file1.py\nfile2.py", stderr="", exit_code=0)
    store.record(action, result)
    messages = store.build_context("task")
    found_assistant = any(m.role == "assistant" and "ls" in m.content for m in messages)
    found_tool = any(m.role == "user" and "file1.py" in m.content for m in messages)
    assert found_assistant
    assert found_tool
