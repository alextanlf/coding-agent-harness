# tests/test_config_loader.py
import pytest
from harness.config.loader import ConfigLoader, HarnessConfig
from pathlib import Path

def test_load_default_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
max_iterations: 15
workspace_dir: ".agent/ws"
model: "gpt-4o"
governance:
  blocked_commands: ["rm -rf"]
  blocked_paths: ["../"]
  require_approval: ["git push"]
  sandbox:
    max_file_size_mb: 5
    allowed_extensions: [".py"]
feedback:
  test_command: "pytest"
  max_retries: 2
""")
    config = ConfigLoader.load(str(config_file))
    assert config.max_iterations == 15
    assert config.workspace_dir == ".agent/ws"
    assert config.model == "gpt-4o"
    assert "rm -rf" in config.governance.blocked_commands
    assert config.governance.sandbox.max_file_size_mb == 5
    assert ".py" in config.governance.sandbox.allowed_extensions
    assert config.feedback.max_retries == 2

def test_load_missing_file_uses_defaults(tmp_path):
    config = ConfigLoader.load(str(tmp_path / "nonexistent.yaml"))
    assert config.max_iterations == 20
    assert config.model == "gpt-4o"

def test_load_invalid_yaml_raises(tmp_path):
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("max_iterations: [unclosed")
    with pytest.raises(ValueError):
        ConfigLoader.load(str(config_file))

def test_config_changes_governance_behavior(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
governance:
  blocked_commands: ["dangerous_cmd"]
  blocked_paths: []
  require_approval: []
  sandbox:
    max_file_size_mb: 10
    allowed_extensions: [".py"]
""")
    config = ConfigLoader.load(str(config_file))
    assert "dangerous_cmd" in config.governance.blocked_commands
