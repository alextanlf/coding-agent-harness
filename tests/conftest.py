# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def workspace_root(tmp_path):
    """Temporary workspace directory for tests."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

@pytest.fixture
def sample_config():
    """Default test config."""
    return {
        "max_iterations": 20,
        "workspace_dir": ".agent/workspace",
        "model": "gpt-4o",
        "governance": {
            "blocked_commands": ["rm -rf", "sudo", "curl.*\\|.*sh"],
            "blocked_paths": ["../", "/etc/", "/root/"],
            "require_approval": ["git push", "pip install", "rm "],
            "sandbox": {
                "max_file_size_mb": 10,
                "allowed_extensions": [".py", ".txt", ".md", ".json", ".yaml"],
            },
        },
        "feedback": {
            "test_command": "pytest tests/ -v --tb=short",
            "max_retries": 3,
        },
    }
