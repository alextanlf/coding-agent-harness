import pytest
from harness.core.action_parser import parse_action, ParseError

def test_parse_task_complete():
    action = parse_action('{"type": "task_complete"}')
    assert action.type == "task_complete"

def test_parse_write_file():
    action = parse_action('{"type": "write_file", "path": "src/foo.py", "content": "print(1)"}')
    assert action.type == "write_file"
    assert action.path == "src/foo.py"
    assert action.content == "print(1)"

def test_parse_run_shell():
    action = parse_action('{"type": "run_shell", "command": "ls -la"}')
    assert action.type == "run_shell"
    assert action.command == "ls -la"

def test_parse_read_file():
    action = parse_action('{"type": "read_file", "path": "bar.py"}')
    assert action.type == "read_file"
    assert action.path == "bar.py"

def test_parse_json_in_markdown_code_block():
    raw = '```json\n{"type": "task_complete"}\n```'
    action = parse_action(raw)
    assert action.type == "task_complete"

def test_parse_invalid_json_raises():
    with pytest.raises(ParseError):
        parse_action("not json at all")

def test_parse_missing_type_raises():
    with pytest.raises(ParseError):
        parse_action('{"path": "foo.py"}')

def test_parse_unknown_type_raises():
    with pytest.raises(ParseError):
        parse_action('{"type": "fly_to_moon"}')
