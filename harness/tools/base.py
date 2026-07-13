# harness/tools/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from harness.core.models import Action


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0


class Tool(ABC):
    @abstractmethod
    async def execute(self, action: Action) -> ToolResult:
        ...


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, action_type: str, tool: Tool):
        self._tools[action_type] = tool

    async def dispatch(self, action: Action) -> ToolResult:
        tool = self._tools.get(action.type)
        if tool is None:
            raise ValueError(f"No tool registered for action type: {action.type}")
        return await tool.execute(action)

