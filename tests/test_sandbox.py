# tests/test_sandbox.py
import pytest
from pathlib import Path
from harness.governance.sandbox import Sandbox
from harness.config.loader import SandboxConfig

@pytest.fixture
def sandbox(workspace_root):
    config = SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py", ".txt"])
    return Sandbox(workspace_root=workspace_root, config=config)

def test_allows_read_inside_workspace(sandbox, workspace_root):
    (workspace_root / "foo.py").write_text("print('hello')")
    decision = sandbox.check_path("foo.py", "read")
    assert decision.allowed is True

def test_blocks_path_traversal(sandbox):
    decision = sandbox.check_path("../../etc/passwd", "read")
    assert decision.allowed is False
    assert "escapes sandbox" in decision.reason

def test_blocks_absolute_path_outside(sandbox):
    decision = sandbox.check_path("/etc/passwd", "read")
    assert decision.allowed is False

def test_blocks_write_bad_extension(sandbox):
    decision = sandbox.check_path("malware.exe", "write")
    assert decision.allowed is False
    assert "Extension" in decision.reason

def test_allows_write_good_extension(sandbox):
    decision = sandbox.check_path("new_file.py", "write")
    assert decision.allowed is True

def test_blocks_read_large_file(sandbox, workspace_root):
    big_file = workspace_root / "big.txt"
    big_file.write_text("x" * (11 * 1024 * 1024))  # 11MB
    decision = sandbox.check_path("big.txt", "read")
    assert decision.allowed is False
    assert "too large" in decision.reason.lower()

def test_allows_read_nonexistent_file(sandbox):
    decision = sandbox.check_path("nonexistent.py", "read")
    assert decision.allowed is True

def test_blocks_symlink_escape(sandbox, workspace_root, tmp_path):
    link_target = tmp_path / "outside.txt"
    link_target.write_text("secret")
    link = workspace_root / "link.py"
    link.symlink_to(link_target)
    decision = sandbox.check_path("link.py", "read")
    assert decision.allowed is False
