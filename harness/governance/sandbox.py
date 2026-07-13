# harness/governance/sandbox.py
from pathlib import Path
from harness.core.models import SandboxDecision
from harness.config.loader import SandboxConfig


class Sandbox:
    """Enforces filesystem boundaries. Pure function, deterministic."""

    def __init__(self, workspace_root: Path, config: SandboxConfig):
        self._workspace_root = workspace_root.resolve()
        self._config = config

    def check_path(self, path: str, operation: str) -> SandboxDecision:
        resolved = (self._workspace_root / path).resolve()

        try:
            resolved.relative_to(self._workspace_root)
        except ValueError:
            return SandboxDecision(allowed=False, reason=f"Path escapes sandbox: {resolved}")

        if operation == "write":
            if resolved.suffix not in self._config.allowed_extensions:
                return SandboxDecision(
                    allowed=False,
                    reason=f"Extension not allowed: {resolved.suffix}",
                )

        if operation == "read" and resolved.exists():
            size_mb = resolved.stat().st_size / 1024 / 1024
            if size_mb > self._config.max_file_size_mb:
                return SandboxDecision(
                    allowed=False,
                    reason=f"File too large: {size_mb:.1f}MB > {self._config.max_file_size_mb}MB",
                )

        return SandboxDecision(allowed=True, reason="ok")
