# harness/config/loader.py
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class SandboxConfig:
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = field(default_factory=lambda: [".py", ".txt", ".md", ".json", ".yaml"])


@dataclass
class GovernanceConfig:
    blocked_commands: list[str] = field(default_factory=lambda: ["rm -rf", "sudo"])
    blocked_paths: list[str] = field(default_factory=lambda: ["../", "/etc/", "/root/"])
    require_approval: list[str] = field(default_factory=lambda: ["git push", "pip install", "rm "])
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)


@dataclass
class FeedbackConfig:
    test_command: str = "pytest tests/ -v --tb=short"
    max_retries: int = 3


@dataclass
class HarnessConfig:
    max_iterations: int = 20
    workspace_dir: str = ".agent/workspace"
    model: str = "gpt-4o"
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)


class ConfigLoader:
    @staticmethod
    def load(path: str) -> HarnessConfig:
        config_path = Path(path)
        if not config_path.exists():
            return HarnessConfig()
        try:
            data = yaml.safe_load(config_path.read_text())
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {path}: {e}")

        if data is None:
            return HarnessConfig()

        gov_data = data.get("governance", {})
        sandbox_data = gov_data.get("sandbox", {})
        fb_data = data.get("feedback", {})

        return HarnessConfig(
            max_iterations=data.get("max_iterations", 20),
            workspace_dir=data.get("workspace_dir", ".agent/workspace"),
            model=data.get("model", "gpt-4o"),
            governance=GovernanceConfig(
                blocked_commands=gov_data.get("blocked_commands", ["rm -rf", "sudo"]),
                blocked_paths=gov_data.get("blocked_paths", ["../", "/etc/", "/root/"]),
                require_approval=gov_data.get("require_approval", ["git push", "pip install", "rm "]),
                sandbox=SandboxConfig(
                    max_file_size_mb=sandbox_data.get("max_file_size_mb", 10),
                    allowed_extensions=sandbox_data.get("allowed_extensions", [".py", ".txt", ".md", ".json", ".yaml"]),
                ),
            ),
            feedback=FeedbackConfig(
                test_command=fb_data.get("test_command", "pytest tests/ -v --tb=short"),
                max_retries=fb_data.get("max_retries", 3),
            ),
        )
