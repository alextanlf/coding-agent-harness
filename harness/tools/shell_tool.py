# harness/tools/shell_tool.py
import asyncio
from harness.tools.base import Tool, ToolResult
from harness.core.models import Action


class RunShellTool(Tool):
    async def execute(self, action: Action) -> ToolResult:
        proc = await asyncio.create_subprocess_shell(
            action.command or "",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
        )
