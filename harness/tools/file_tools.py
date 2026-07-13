# harness/tools/file_tools.py
from pathlib import Path
from harness.tools.base import Tool, ToolResult
from harness.core.models import Action
from harness.governance.sandbox import Sandbox


class ReadFileTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or "", "read")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        try:
            workspace_root = self._sandbox._workspace_root
            content = (workspace_root / action.path).read_text()
            return ToolResult(success=True, output=content)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {action.path}")


class WriteFileTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or "", "write")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        workspace_root = self._sandbox._workspace_root
        file_path = workspace_root / action.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(action.content or "")
        return ToolResult(success=True, output=f"Wrote {action.path}")


class ListFilesTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or ".", "read")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        workspace_root = self._sandbox._workspace_root
        target = workspace_root / (action.path or ".")
        if not target.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {action.path}")
        files = [str(f.relative_to(workspace_root)) for f in target.rglob("*") if f.is_file()]
        return ToolResult(success=True, output="\n".join(sorted(files)))
