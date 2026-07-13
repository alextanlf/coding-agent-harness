# tests/test_tools.py
import pytest
from pathlib import Path
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import ReadFileTool, WriteFileTool, ListFilesTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.sandbox import Sandbox
from harness.config.loader import SandboxConfig
from harness.core.models import Action, ShellResult

@pytest.fixture
def registry(workspace_root):
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py", ".txt"]))
    reg = ToolRegistry()
    reg.register("read_file", ReadFileTool(sandbox))
    reg.register("write_file", WriteFileTool(sandbox))
    reg.register("list_files", ListFilesTool(sandbox))
    reg.register("run_shell", RunShellTool())
    return reg

@pytest.mark.asyncio
async def test_write_then_read(registry, workspace_root):
    write_action = Action(type="write_file", path="hello.py", content="print('hi')")
    result = await registry.dispatch(write_action)
    assert result.success is True

    read_action = Action(type="read_file", path="hello.py")
    result = await registry.dispatch(read_action)
    assert "print('hi')" in result.output

@pytest.mark.asyncio
async def test_write_blocked_by_sandbox(registry):
    action = Action(type="write_file", path="../../etc/evil.py", content="bad")
    result = await registry.dispatch(action)
    assert result.success is False
    assert "escapes sandbox" in result.error

@pytest.mark.asyncio
async def test_list_files(registry, workspace_root):
    (workspace_root / "a.py").write_text("x")
    (workspace_root / "b.py").write_text("y")
    action = Action(type="list_files", path=".")
    result = await registry.dispatch(action)
    assert "a.py" in result.output
    assert "b.py" in result.output

@pytest.mark.asyncio
async def test_run_shell(registry):
    action = Action(type="run_shell", command="echo hello")
    result = await registry.dispatch(action)
    assert "hello" in result.output
    assert result.exit_code == 0

@pytest.mark.asyncio
async def test_unknown_action_type_raises(registry):
    action = Action(type="unknown")
    with pytest.raises(ValueError):
        await registry.dispatch(action)
