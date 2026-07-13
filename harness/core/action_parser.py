import json
import re
from harness.core.models import Action


VALID_TYPES = {"read_file", "write_file", "list_files", "run_shell", "run_tests", "task_complete"}


class ParseError(Exception):
    pass


def parse_action(raw: str) -> Action:
    cleaned = _strip_markdown_fence(raw).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON response: {e}\nRaw: {raw[:200]}")

    if not isinstance(data, dict):
        raise ParseError(f"Expected JSON object, got {type(data).__name__}")
    if "type" not in data:
        raise ParseError("Missing 'type' field in action")

    action_type = data["type"]
    if action_type not in VALID_TYPES:
        raise ParseError(f"Unknown action type: '{action_type}'. Valid: {VALID_TYPES}")

    return Action(
        type=action_type,
        path=data.get("path"),
        content=data.get("content"),
        command=data.get("command"),
    )


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
