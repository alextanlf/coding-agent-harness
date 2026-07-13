from harness.core.models import Message, Action, ShellResult


class MemoryStore:
    """Session-scoped memory. Stores action history, builds LLM context."""

    def __init__(self, system_prompt: str = "You are a coding agent.", max_context_actions: int = 10):
        self._system_prompt = system_prompt
        self._max_context = max_context_actions
        self._history: list[Message] = []

    def record(self, action: Action, result: ShellResult):
        self._history.append(Message(
            role="assistant",
            content=self._format_action(action),
        ))
        self._history.append(Message(
            role="user",
            content=f"Tool result:\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}\nexit_code: {result.exit_code}",
        ))

    def build_context(self, task: str) -> list[Message]:
        messages = [Message(role="system", content=self._system_prompt)]
        recent = self._history[-self._max_context * 2:] if self._max_context > 0 else self._history
        messages.extend(recent)
        messages.append(Message(role="user", content=f"Task: {task}"))
        return messages

    def _format_action(self, action: Action) -> str:
        parts = [f"type: {action.type}"]
        if action.path:
            parts.append(f"path: {action.path}")
        if action.command:
            parts.append(f"command: {action.command}")
        if action.content:
            parts.append(f"content: {action.content[:200]}")
        return " | ".join(parts)
