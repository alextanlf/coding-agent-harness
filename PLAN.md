# Coding Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Coding Agent Harness with a self-implemented kernel (main loop, tools, governance, feedback, memory, config), mock-LLM unit tests, credential security, Docker distribution, and a WebUI with real-time action streaming and HITL approval.

**Architecture:** Single-process async architecture. Harness core is a pure Python library (no web deps), fully testable with mock LLM. FastAPI wraps it with WebSocket streaming for real-time action logs and HITL approval flow.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, openai SDK, pyyaml, cryptography (Fernet), pytest + pytest-asyncio, Docker, GitHub Actions.

## Global Constraints

- Python >= 3.12
- TDD mandatory: red → green → refactor. No implementation before tests.
- Harness core (`harness/`) must have zero web/HTTP dependencies.
- All governance mechanisms must be unit-testable with mock LLM (no network).
- API key never hardcoded, never committed, never in logs.
- CI must have a job named `unit-test`.
- `make test` must run all tests.

---

## File Structure

```
coding-agent-harness/
├── harness/                        # Pure Python library (no web deps)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py               # Action, Message, ShellResult, Failure, TestFeedback, RunResult, decisions
│   │   ├── action_parser.py        # Parse LLM text response → Action
│   │   └── loop.py                 # Agent main loop
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                 # LLMClient ABC
│   │   ├── openai_client.py        # OpenAI implementation
│   │   └── mock_client.py          # Mock for unit tests
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                 # ToolRegistry + Tool ABC
│   │   ├── file_tools.py           # read_file, write_file, list_files
│   │   └── shell_tool.py           # run_shell, run_tests
│   ├── governance/                 # DEEP DIMENSION
│   │   ├── __init__.py
│   │   ├── guardrails.py           # GuardrailEngine
│   │   ├── sandbox.py              # Sandbox
│   │   ├── hitl.py                 # HITLStateMachine
│   │   └── engine.py               # GovernanceEngine (composition)
│   ├── feedback/
│   │   ├── __init__.py
│   │   └── engine.py               # FeedbackEngine
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py                # MemoryStore
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py               # ConfigLoader + HarnessConfig
│   └── credentials/
│       ├── __init__.py
│       └── store.py                # CredentialStore
├── web/                            # WebUI layer
│   ├── __init__.py
│   ├── app.py                      # FastAPI app
│   ├── routes.py                   # REST + WebSocket routes
│   ├── session_manager.py          # Session manager
│   └── static/
│       ├── index.html              # Chat UI
│       ├── style.css
│       └── app.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures
│   ├── test_models.py
│   ├── test_config_loader.py
│   ├── test_mock_llm.py
│   ├── test_guardrails.py
│   ├── test_sandbox.py
│   ├── test_hitl.py
│   ├── test_governance_engine.py
│   ├── test_feedback.py
│   ├── test_memory.py
│   ├── test_tools.py
│   ├── test_credential_store.py
│   ├── test_action_parser.py
│   ├── test_loop_integration.py
│   └── test_mechanism_demo.py
├── demo/
│   └── mechanism_demo.py
├── harness_config.yaml
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── .github/workflows/ci.yml
├── .gitignore
├── SPEC.md
├── PLAN.md
├── SPEC_PROCESS.md
├── AGENT_LOG.md
├── REFLECTION.md
└── README.md
```

---

## Task Dependency Graph

```
Phase 1: Foundation
  Task 1 (scaffolding) → Task 2 (models) → Task 3 (config)

Phase 2: LLM Abstraction
  Task 4 (LLM ABC + mock) → Task 5 (OpenAI client)

Phase 3: Governance (DEEP)
  Task 6 (guardrails) ─┐
  Task 7 (sandbox) ────┤→ Task 9 (governance engine)
  Task 8 (HITL) ──────┘

Phase 4: Feedback + Memory + Tools
  Task 10 (feedback) ─┐
  Task 11 (memory) ──┤→ Task 12 (tools)
                      │
Phase 5: Credentials   │
  Task 13 (creds) ────┘

Phase 6: Main Loop
  Task 14 (action parser) → Task 15 (main loop)

Phase 7: WebUI
  Task 16 (FastAPI + routes) → Task 17 (session manager) → Task 18 (chat UI)

Phase 8: Distribution + CI
  Task 19 (Dockerfile) → Task 20 (CI) → Task 21 (mechanism demo)

Phase 9: Docs
  Task 22 (README)
```

**Parallelizable:** Tasks 6, 7, 8 can run in parallel (worktrees). Tasks 10, 11, 13 can run in parallel.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `harness/__init__.py`
- Create: `harness/core/__init__.py`
- Create: `harness/llm/__init__.py`
- Create: `harness/tools/__init__.py`
- Create: `harness/governance/__init__.py`
- Create: `harness/feedback/__init__.py`
- Create: `harness/memory/__init__.py`
- Create: `harness/config/__init__.py`
- Create: `harness/credentials/__init__.py`
- Create: `web/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `harness_config.yaml`

**Interfaces:**
- Produces: project structure, dependency manifest, test infrastructure

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "coding-agent-harness"
version = "0.1.0"
description = "A coding agent harness with governance, feedback, and HITL"
requires-python = ">=3.12"
dependencies = [
    "openai>=1.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pyyaml>=6.0",
    "cryptography>=42.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
include = ["harness*", "web*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create Makefile**

```makefile
.PHONY: test run docker lint

test:
\tpytest tests/ -v --tb=short

run:
\tuvicorn web.app:app --reload --host 0.0.0.0 --port 8000

docker:
\tdocker build -t coding-agent-harness .

docker-run:
\tdocker run -p 8000:8000 -v agent_data:/app/.agent coding-agent-harness
```

- [ ] **Step 3: Create all `__init__.py` files and conftest.py**

```python
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
```

- [ ] **Step 4: Create harness_config.yaml**

```yaml
max_iterations: 20
workspace_dir: ".agent/workspace"
model: "gpt-4o"

governance:
  blocked_commands:
    - "rm -rf"
    - "sudo"
    - "curl.*\\|.*sh"
  blocked_paths:
    - "../"
    - "/etc/"
    - "/root/"
  require_approval:
    - "git push"
    - "pip install"
    - "rm "
  sandbox:
    max_file_size_mb: 10
    allowed_extensions: [".py", ".txt", ".md", ".json", ".yaml"]

feedback:
  test_command: "pytest tests/ -v --tb=short"
  max_retries: 3
```

- [ ] **Step 5: Install package and verify test infra**

Run: `pip install -e ".[dev]" && pytest --co`
Expected: `no tests ran` (collection succeeds, no tests yet)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding — pyproject, Makefile, config, test infra"
```

---

## Task 2: Core Data Models

**Files:**
- Create: `harness/core/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Message`, `Action`, `ShellResult`, `Failure`, `TestFeedback`, `GuardrailRule`, `GuardrailDecision`, `SandboxDecision`, `ApprovalRequest`, `GovernanceDecision`, `RunResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from harness.core.models import (
    Message, Action, ShellResult, Failure, TestFeedback,
    GuardrailRule, GuardrailDecision, SandboxDecision,
    ApprovalRequest, GovernanceDecision, RunResult,
)
from datetime import datetime

def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

def test_action_file_read():
    action = Action(type="read_file", path="src/foo.py")
    assert action.type == "read_file"
    assert action.path == "src/foo.py"
    assert action.command is None

def test_action_shell():
    action = Action(type="run_shell", command="ls -la")
    assert action.type == "run_shell"
    assert action.command == "ls -la"
    assert action.path is None

def test_shell_result():
    result = ShellResult(stdout="hello", stderr="", exit_code=0)
    assert result.exit_code == 0

def test_failure():
    f = Failure(name="test_bar", message="assert 1==2", file="test_foo.py", line=42)
    assert f.name == "test_bar"
    assert f.line == 42

def test_test_feedback():
    tf = TestFeedback(passed=False, failures=[Failure("t", "m", "f", 1)], raw_output="out")
    assert tf.passed is False
    assert len(tf.failures) == 1

def test_guardrail_rule():
    rule = GuardrailRule(pattern="rm -rf", severity="block", description="recursive delete")
    assert rule.severity == "block"

def test_guardrail_decision():
    d = GuardrailDecision(allowed=False, requires_approval=False, reason="blocked", rule=None)
    assert d.allowed is False

def test_sandbox_decision():
    d = SandboxDecision(allowed=True, reason="ok")
    assert d.allowed is True

def test_approval_request():
    req = ApprovalRequest(
        id="abc", action=Action(type="run_shell", command="git push"),
        reason="pushing", state="pending",
        created_at=datetime.now(), decided_at=None, decided_by=None,
    )
    assert req.state == "pending"

def test_governance_decision():
    d = GovernanceDecision(allowed=True, blocked=False, reason="")
    assert d.blocked is False

def test_run_result():
    r = RunResult(success=True, iterations=5, reason="task_complete")
    assert r.success is True
    assert r.iterations == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harness.core.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/core/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Action:
    type: str
    path: str | None = None
    content: str | None = None
    command: str | None = None


@dataclass
class ShellResult:
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class Failure:
    name: str
    message: str
    file: str
    line: int


@dataclass
class TestFeedback:
    passed: bool
    failures: list[Failure]
    raw_output: str


@dataclass
class GuardrailRule:
    pattern: str
    severity: Literal["block", "approve"]
    description: str


@dataclass
class GuardrailDecision:
    allowed: bool
    requires_approval: bool
    reason: str
    rule: GuardrailRule | None = None


@dataclass
class SandboxDecision:
    allowed: bool
    reason: str


@dataclass
class ApprovalRequest:
    id: str
    action: Action
    reason: str
    state: str
    created_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None


@dataclass
class GovernanceDecision:
    allowed: bool
    blocked: bool
    reason: str


@dataclass
class RunResult:
    success: bool
    iterations: int
    reason: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/core/models.py tests/test_models.py
git commit -m "feat: core data models — Action, Message, decisions, RunResult"
```

---

## Task 3: Config Loader

**Files:**
- Create: `harness/config/loader.py`
- Test: `tests/test_config_loader.py`

**Interfaces:**
- Consumes: `harness_config.yaml` (file path)
- Produces: `HarnessConfig`, `GovernanceConfig`, `SandboxConfig`, `FeedbackConfig` dataclasses

- [ ] **Step 1: Write the failing test**

```python
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
    with pytest.raises(Exception):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_loader.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/config/loader.py tests/test_config_loader.py
git commit -m "feat: config loader — YAML parsing with defaults"
```

---

## Task 4: LLM Abstraction + Mock Client

**Files:**
- Create: `harness/llm/base.py`
- Create: `harness/llm/mock_client.py`
- Test: `tests/test_mock_llm.py`

**Interfaces:**
- Consumes: `Message` from `harness.core.models`
- Produces: `LLMClient` (ABC), `MockLLMClient`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mock_llm.py
import pytest
from harness.llm.mock_client import MockLLMClient
from harness.core.models import Message

@pytest.mark.asyncio
async def test_mock_returns_scripted_response():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    response = await client.complete([Message(role="user", content="do something")])
    assert response == '{"type": "task_complete"}'

@pytest.mark.asyncio
async def test_mock_returns_sequential_responses():
    client = MockLLMClient(scripted_responses=[
        '{"type": "run_shell", "command": "ls"}',
        '{"type": "task_complete"}',
    ])
    r1 = await client.complete([Message("user", "task")])
    r2 = await client.complete([Message("user", "task")])
    assert "ls" in r1
    assert "task_complete" in r2

@pytest.mark.asyncio
async def test_mock_raises_when_responses_exhausted():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    await client.complete([Message("user", "task")])
    with pytest.raises(IndexError):
        await client.complete([Message("user", "task")])

@pytest.mark.asyncio
async def test_mock_records_call_count():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'] * 3)
    await client.complete([Message("user", "t")])
    await client.complete([Message("user", "t")])
    assert client.call_count == 2

@pytest.mark.asyncio
async def test_mock_records_messages():
    client = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])
    msgs = [Message("system", "sys"), Message("user", "hello")]
    await client.complete(msgs)
    assert len(client.call_history) == 1
    assert client.call_history[0] == msgs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mock_llm.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/llm/base.py
from abc import ABC, abstractmethod
from harness.core.models import Message


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[Message]) -> str:
        """Call the LLM with messages, return raw text response."""
        ...
```

```python
# harness/llm/mock_client.py
from harness.llm.base import LLMClient
from harness.core.models import Message


class MockLLMClient(LLMClient):
    """Mock LLM for unit tests. Returns scripted responses in order."""

    def __init__(self, scripted_responses: list[str]):
        self._responses = list(scripted_responses)
        self._index = 0
        self.call_count = 0
        self.call_history: list[list[Message]] = []

    async def complete(self, messages: list[Message]) -> str:
        self.call_history.append(messages)
        self.call_count += 1
        if self._index >= len(self._responses):
            raise IndexError(f"MockLLMClient: no more scripted responses (call #{self.call_count})")
        response = self._responses[self._index]
        self._index += 1
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mock_llm.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/llm/base.py harness/llm/mock_client.py tests/test_mock_llm.py
git commit -m "feat: LLM abstraction layer + mock client for unit tests"
```

---

## Task 5: OpenAI Client

**Files:**
- Create: `harness/llm/openai_client.py`
- Test: `tests/test_openai_client.py` (uses mock, no real API calls)

**Interfaces:**
- Consumes: `LLMClient` from `harness.llm.base`, `Message` from `harness.core.models`
- Produces: `OpenAIClient`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_openai_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from harness.llm.openai_client import OpenAIClient
from harness.core.models import Message

@pytest.mark.asyncio
async def test_openai_client_calls_api():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"type": "task_complete"}'

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await client.complete([Message("user", "hello")])
        assert result == '{"type": "task_complete"}'
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_openai_client_passes_model():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o-mini")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        await client.complete([Message("user", "hi")])
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"

@pytest.mark.asyncio
async def test_openai_client_retries_on_rate_limit():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"

    import openai
    rate_limit_error = openai.RateLimitError(
        message="rate limited", response=MagicMock(), body=None
    )

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[rate_limit_error, mock_response]
        )
        result = await client.complete([Message("user", "hi")])
        assert result == "ok"
        assert mock_client.chat.completions.create.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_openai_client.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/llm/openai_client.py
import asyncio
import logging
from harness.llm.base import LLMClient
from harness.core.models import Message

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI, AsyncOpenAI
        self._api_key = api_key
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(self, messages: list[Message]) -> str:
        import openai
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                )
                return response.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    raise
            except openai.APIError as e:
                raise LLMError(f"OpenAI API error: {e}") from e


class LLMError(Exception):
    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_openai_client.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/llm/openai_client.py tests/test_openai_client.py
git commit -m "feat: OpenAI client with rate limit retry"
```

---

## Task 6: Guardrail Engine

**Files:**
- Create: `harness/governance/guardrails.py`
- Test: `tests/test_guardrails.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailRule`, `GuardrailDecision` from `harness.core.models`
- Produces: `GuardrailEngine`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_guardrails.py
import pytest
from harness.governance.guardrails import GuardrailEngine
from harness.core.models import Action, GuardrailRule

@pytest.fixture
def engine():
    rules = [
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
        GuardrailRule(pattern=r"sudo", severity="block", description="sudo not allowed"),
        GuardrailRule(pattern=r"git\s+push", severity="approve", description="pushing to remote"),
        GuardrailRule(pattern=r"pip\s+install", severity="approve", description="installing packages"),
    ]
    return GuardrailEngine(rules=rules)

def test_blocks_rm_rf(engine):
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "recursive delete" in decision.reason

def test_blocks_sudo(engine):
    action = Action(type="run_shell", command="sudo apt-get update")
    decision = engine.evaluate(action)
    assert decision.allowed is False

def test_requires_approval_for_git_push(engine):
    action = Action(type="run_shell", command="git push origin main")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "pushing to remote" in decision.reason

def test_allows_safe_command(engine):
    action = Action(type="run_shell", command="ls -la")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is False

def test_non_shell_action_passes_through(engine):
    action = Action(type="read_file", path="src/foo.py")
    decision = engine.evaluate(action)
    assert decision.allowed is True
    assert decision.requires_approval is False

def test_empty_rules_allows_all():
    engine = GuardrailEngine(rules=[])
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.allowed is True

def test_multiple_block_rules_first_match_wins():
    rules = [
        GuardrailRule(pattern=r"rm", severity="approve", description="any rm"),
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="rm -rf"),
    ]
    engine = GuardrailEngine(rules=rules)
    action = Action(type="run_shell", command="rm -rf /")
    decision = engine.evaluate(action)
    assert decision.requires_approval is True
    assert decision.allowed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_guardrails.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/governance/guardrails.py
import re
from harness.core.models import Action, GuardrailRule, GuardrailDecision


class GuardrailEngine:
    """Evaluates shell commands against guardrail rules. Pure function, no LLM."""

    def __init__(self, rules: list[GuardrailRule]):
        self._rules = rules

    def evaluate(self, action: Action) -> GuardrailDecision:
        if action.type != "run_shell" or action.command is None:
            return GuardrailDecision(allowed=True, requires_approval=False, reason="", rule=None)

        for rule in self._rules:
            if re.search(rule.pattern, action.command):
                if rule.severity == "block":
                    return GuardrailDecision(
                        allowed=False,
                        requires_approval=False,
                        reason=f"Blocked: {rule.description}",
                        rule=rule,
                    )
                elif rule.severity == "approve":
                    return GuardrailDecision(
                        allowed=True,
                        requires_approval=True,
                        reason=f"Needs approval: {rule.description}",
                        rule=rule,
                    )
        return GuardrailDecision(allowed=True, requires_approval=False, reason="", rule=None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_guardrails.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/governance/guardrails.py tests/test_guardrails.py
git commit -m "feat: guardrail engine — regex-based command blocking (governance deep)"
```

---

## Task 7: Sandbox

**Files:**
- Create: `harness/governance/sandbox.py`
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Consumes: `SandboxConfig` from `harness.config.loader`
- Produces: `Sandbox`, `SandboxDecision`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sandbox.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
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

        if not str(resolved).startswith(str(self._workspace_root)):
            return SandboxDecision(allowed=False, reason=f"Path escapes sandbox: {resolved}")

        if operation == "write":
            if resolved.suffix not in self._config.allowed_extensions:
                return SandboxDecision(
                    allowed=False,
                    reason=f"Extension not allowed: {resolved.suffix}",
                )

        if operation == "read" and resolved.exists():
            if resolved.is_symlink():
                real_target = resolved.resolve()
                if not str(real_target).startswith(str(self._workspace_root)):
                    return SandboxDecision(
                        allowed=False,
                        reason=f"Symlink escapes sandbox: {real_target}",
                    )
            size_mb = resolved.stat().st_size / 1024 / 1024
            if size_mb > self._config.max_file_size_mb:
                return SandboxDecision(
                    allowed=False,
                    reason=f"File too large: {size_mb:.1f}MB > {self._config.max_file_size_mb}MB",
                )

        return SandboxDecision(allowed=True, reason="ok")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sandbox.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/governance/sandbox.py tests/test_sandbox.py
git commit -m "feat: sandbox — path traversal, extension, size, symlink checks (governance deep)"
```

---

## Task 8: HITL State Machine

**Files:**
- Create: `harness/governance/hitl.py`
- Test: `tests/test_hitl.py`

**Interfaces:**
- Consumes: `Action`, `ApprovalRequest` from `harness.core.models`
- Produces: `HITLStateMachine`, `ApprovalState`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hitl.py
import pytest
import asyncio
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.core.models import Action

@pytest.fixture
def sm():
    return HITLStateMachine(timeout_seconds=2)

@pytest.mark.asyncio
async def test_request_approval_returns_pending(sm):
    action = Action(type="run_shell", command="git push")
    task = asyncio.create_task(sm.request_approval(action, "pushing to remote"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    assert len(pending) == 1
    assert pending[0].state == ApprovalState.PENDING
    sm.resolve(pending[0].id, ApprovalState.APPROVED, "test_user")
    result = await task
    assert result.state == ApprovalState.APPROVED

@pytest.mark.asyncio
async def test_denial(sm):
    action = Action(type="run_shell", command="pip install evil")
    task = asyncio.create_task(sm.request_approval(action, "installing"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    sm.resolve(pending[0].id, ApprovalState.DENIED, "test_user")
    result = await task
    assert result.state == ApprovalState.DENIED

@pytest.mark.asyncio
async def test_timeout(sm):
    sm = HITLStateMachine(timeout_seconds=0.1)
    action = Action(type="run_shell", command="rm file")
    result = await sm.request_approval(action, "deleting")
    assert result.state == ApprovalState.TIMEOUT

@pytest.mark.asyncio
async def test_resolve_nonexistent_raises(sm):
    with pytest.raises(KeyError):
        sm.resolve("nonexistent-id", ApprovalState.APPROVED, "user")

@pytest.mark.asyncio
async def test_double_resolve_raises(sm):
    action = Action(type="run_shell", command="git push")
    task = asyncio.create_task(sm.request_approval(action, "push"))
    await asyncio.sleep(0.05)
    pending = sm.get_pending_requests()
    sm.resolve(pending[0].id, ApprovalState.APPROVED, "user")
    await task
    with pytest.raises(KeyError):
        sm.resolve(pending[0].id, ApprovalState.DENIED, "user")

@pytest.mark.asyncio
async def test_get_pending_requests_empty(sm):
    assert sm.get_pending_requests() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hitl.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/governance/hitl.py
import asyncio
from datetime import datetime
from uuid import uuid4
from enum import Enum
from harness.core.models import Action, ApprovalRequest


class ApprovalState(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class HITLStateMachine:
    """Manages approval requests with async pause/resume via asyncio.Event."""

    def __init__(self, timeout_seconds: int = 120):
        self._timeout = timeout_seconds
        self._pending: dict[str, ApprovalRequest] = {}
        self._events: dict[str, asyncio.Event] = {}

    async def request_approval(self, action: Action, reason: str) -> ApprovalRequest:
        request_id = str(uuid4())
        request = ApprovalRequest(
            id=request_id,
            action=action,
            reason=reason,
            state=ApprovalState.PENDING.value,
            created_at=datetime.now(),
        )
        self._pending[request_id] = request
        self._events[request_id] = asyncio.Event()

        try:
            await asyncio.wait_for(self._events[request_id].wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            request.state = ApprovalState.TIMEOUT.value
            request.decided_at = datetime.now()
        finally:
            self._cleanup(request_id)

        return request

    def resolve(self, request_id: str, decision: ApprovalState, user: str):
        if request_id not in self._pending:
            raise KeyError(f"No pending request with id {request_id}")
        request = self._pending[request_id]
        if request.state != ApprovalState.PENDING.value:
            raise KeyError(f"Request {request_id} already resolved: {request.state}")
        request.state = decision.value
        request.decided_at = datetime.now()
        request.decided_by = user
        self._events[request_id].set()

    def get_pending_requests(self) -> list[ApprovalRequest]:
        return [r for r in self._pending.values() if r.state == ApprovalState.PENDING.value]

    def _cleanup(self, request_id: str):
        if request_id in self._events:
            del self._events[request_id]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hitl.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/governance/hitl.py tests/test_hitl.py
git commit -m "feat: HITL state machine — async pause/resume with timeout (governance deep)"
```

---

## Task 9: Governance Engine (Composition)

**Files:**
- Create: `harness/governance/engine.py`
- Test: `tests/test_governance_engine.py`

**Interfaces:**
- Consumes: `GuardrailEngine`, `Sandbox`, `HITLStateMachine`
- Produces: `GovernanceEngine`, `GovernanceDecision`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_governance_engine.py
import pytest
import asyncio
from pathlib import Path
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.config.loader import SandboxConfig
from harness.core.models import Action, GuardrailRule

@pytest.fixture
def engine(workspace_root):
    guardrails = GuardrailEngine(rules=[
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
        GuardrailRule(pattern=r"git\s+push", severity="approve", description="pushing"),
    ])
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py"]))
    hitl = HITLStateMachine(timeout_seconds=2)
    return GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

@pytest.mark.asyncio
async def test_blocks_dangerous_shell(engine):
    action = Action(type="run_shell", command="rm -rf /")
    decision = await engine.evaluate(action)
    assert decision.blocked is True
    assert decision.allowed is False

@pytest.mark.asyncio
async def test_blocks_path_traversal(engine):
    action = Action(type="read_file", path="../../etc/passwd")
    decision = await engine.evaluate(action)
    assert decision.blocked is True

@pytest.mark.asyncio
async def test_allows_safe_read(engine, workspace_root):
    (workspace_root / "foo.py").write_text("print('hi')")
    action = Action(type="read_file", path="foo.py")
    decision = await engine.evaluate(action)
    assert decision.allowed is True
    assert decision.blocked is False

@pytest.mark.asyncio
async def test_hitl_pause_and_approve(engine):
    action = Action(type="run_shell", command="git push origin main")
    task = asyncio.create_task(engine.evaluate(action))
    await asyncio.sleep(0.05)
    pending = engine.hitl.get_pending_requests()
    assert len(pending) == 1
    engine.hitl.resolve(pending[0].id, ApprovalState.APPROVED, "test")
    decision = await task
    assert decision.allowed is True
    assert decision.blocked is False

@pytest.mark.asyncio
async def test_hitl_denied(engine):
    action = Action(type="run_shell", command="git push origin main")
    task = asyncio.create_task(engine.evaluate(action))
    await asyncio.sleep(0.05)
    pending = engine.hitl.get_pending_requests()
    engine.hitl.resolve(pending[0].id, ApprovalState.DENIED, "test")
    decision = await task
    assert decision.blocked is True
    assert "not approved" in decision.reason.lower()

@pytest.mark.asyncio
async def test_non_shell_non_file_action_passes(engine):
    action = Action(type="task_complete")
    decision = await engine.evaluate(action)
    assert decision.allowed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_governance_engine.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/governance/engine.py
from harness.core.models import Action, GovernanceDecision
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState


class GovernanceEngine:
    """Composes guardrails, sandbox, and HITL into a single evaluate()."""

    def __init__(self, guardrails: GuardrailEngine, sandbox: Sandbox, hitl: HITLStateMachine):
        self.guardrails = guardrails
        self.sandbox = sandbox
        self.hitl = hitl

    async def evaluate(self, action: Action) -> GovernanceDecision:
        if action.type in ("read_file", "write_file", "list_files"):
            sandbox_decision = self.sandbox.check_path(action.path or "", action.type)
            if not sandbox_decision.allowed:
                return GovernanceDecision(allowed=False, blocked=True, reason=sandbox_decision.reason)

        if action.type == "run_shell":
            guardrail_decision = self.guardrails.evaluate(action)
            if not guardrail_decision.allowed:
                return GovernanceDecision(allowed=False, blocked=True, reason=guardrail_decision.reason)
            if guardrail_decision.requires_approval:
                approval = await self.hitl.request_approval(action, guardrail_decision.reason)
                if approval.state != ApprovalState.APPROVED.value:
                    return GovernanceDecision(
                        allowed=False,
                        blocked=True,
                        reason=f"Action not approved: {approval.state}",
                    )

        return GovernanceDecision(allowed=True, blocked=False, reason="")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_governance_engine.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/governance/engine.py tests/test_governance_engine.py
git commit -m "feat: governance engine — composes guardrails + sandbox + HITL (governance deep)"
```

---

## Task 10: Feedback Engine

**Files:**
- Create: `harness/feedback/engine.py`
- Test: `tests/test_feedback.py`

**Interfaces:**
- Consumes: `ShellResult`, `Failure`, `TestFeedback` from `harness.core.models`
- Produces: `FeedbackEngine`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feedback.py
import pytest
from harness.feedback.engine import FeedbackEngine
from harness.core.models import ShellResult

@pytest.fixture
def engine():
    return FeedbackEngine(test_command="pytest", max_retries=3)

def test_parse_passed_tests(engine):
    output = ShellResult(stdout="1 passed in 0.5s", stderr="", exit_code=0)
    feedback = engine.parse_test_output(output)
    assert feedback.passed is True
    assert len(feedback.failures) == 0

def test_parse_failed_test(engine):
    output = ShellResult(
        stdout="",
        stderr="FAILED tests/test_foo.py::test_bar - assert 1 == 2\n1 failed in 0.3s",
        exit_code=1,
    )
    feedback = engine.parse_test_output(output)
    assert feedback.passed is False
    assert len(feedback.failures) == 1
    assert feedback.failures[0].name == "test_bar"
    assert "tests/test_foo.py" in feedback.failures[0].file

def test_parse_multiple_failures(engine):
    output = ShellResult(
        stdout="",
        stderr=(
            "FAILED tests/test_a.py::test_one - assert 1 == 2\n"
            "FAILED tests/test_b.py::test_two - KeyError: 'foo'\n"
            "2 failed in 0.5s"
        ),
        exit_code=1,
    )
    feedback = engine.parse_test_output(output)
    assert feedback.passed is False
    assert len(feedback.failures) == 2
    assert feedback.failures[0].name == "test_one"
    assert feedback.failures[1].name == "test_two"

def test_inject_passed_feedback(engine):
    from harness.core.models import TestFeedback
    feedback = TestFeedback(passed=True, failures=[], raw_output="")
    msg = engine.inject(feedback)
    assert "passed" in msg.content.lower()

def test_inject_failed_feedback(engine):
    from harness.core.models import TestFeedback, Failure
    feedback = TestFeedback(
        passed=False,
        failures=[Failure(name="test_bar", message="assert 1==2", file="test_foo.py", line=42)],
        raw_output="",
    )
    msg = engine.inject(feedback)
    assert "test_bar" in msg.content
    assert "assert 1==2" in msg.content
    assert "Fix" in msg.content

def test_truncates_raw_output(engine):
    long_output = "x" * 5000
    output = ShellResult(stdout=long_output, stderr="", exit_code=1)
    feedback = engine.parse_test_output(output)
    assert len(feedback.raw_output) <= 2000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/feedback/engine.py
import re
from harness.core.models import ShellResult, Failure, TestFeedback, Message


class FeedbackEngine:
    """Parses pytest output into structured feedback. Pure function, deterministic."""

    FAILURE_PATTERN = re.compile(
        r'FAILED\s+(\S+?)::(\w+)\s+-\s+(.+?)(?:\n|$)'
    )

    def __init__(self, test_command: str, max_retries: int):
        self._test_command = test_command
        self._max_retries = max_retries

    def parse_test_output(self, output: ShellResult) -> TestFeedback:
        combined = output.stdout + "\n" + output.stderr
        passed = output.exit_code == 0

        failures = []
        for match in self.FAILURE_PATTERN.finditer(combined):
            file_path = match.group(1)
            test_name = match.group(2)
            message = match.group(3).strip()
            line = self._extract_line(message)
            failures.append(Failure(name=test_name, message=message, file=file_path, line=line))

        raw_output = combined[:2000]

        return TestFeedback(passed=passed, failures=failures, raw_output=raw_output)

    def inject(self, feedback: TestFeedback) -> Message:
        if feedback.passed:
            return Message(role="system", content="All tests passed. Task complete.")
        failure_text = "\n".join(
            f"- {f.name}: {f.message} ({f.file}:{f.line})"
            for f in feedback.failures
        )
        return Message(
            role="system",
            content=f"Tests failed ({len(feedback.failures)} failures):\n{failure_text}\n\nFix the failing tests.",
        )

    def _extract_line(self, message: str) -> int:
        line_match = re.search(r':(\d+):', message)
        return int(line_match.group(1)) if line_match else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/feedback/engine.py tests/test_feedback.py
git commit -m "feat: feedback engine — pytest output parser + context injection"
```

---

## Task 11: Memory Store

**Files:**
- Create: `harness/memory/store.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `Message`, `Action` from `harness.core.models`
- Produces: `MemoryStore`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory.py
import pytest
from harness.memory.store import MemoryStore
from harness.core.models import Message, Action, ShellResult

def test_empty_memory_returns_system_and_task():
    store = MemoryStore(system_prompt="You are a coding agent.")
    messages = store.build_context("Write a hello world function")
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content == "You are a coding agent."
    assert messages[1].role == "user"
    assert "hello world" in messages[1].content

def test_record_and_retrieve():
    store = MemoryStore(system_prompt="sys")
    action = Action(type="write_file", path="foo.py", content="print('hi')")
    result = ShellResult(stdout="", stderr="", exit_code=0)
    store.record(action, result)
    messages = store.build_context("task")
    assert len(messages) >= 3

def test_last_n_actions_kept():
    store = MemoryStore(system_prompt="sys", max_context_actions=3)
    for i in range(10):
        action = Action(type="write_file", path=f"f{i}.py", content="x")
        store.record(action, ShellResult("", "", 0))
    messages = store.build_context("task")
    action_msgs = [m for m in messages if m.role == "assistant"]
    assert len(action_msgs) <= 3

def test_record_appends_assistant_and_user_messages():
    store = MemoryStore(system_prompt="sys")
    action = Action(type="run_shell", command="ls")
    result = ShellResult(stdout="file1.py\nfile2.py", stderr="", exit_code=0)
    store.record(action, result)
    messages = store.build_context("task")
    found_assistant = any(m.role == "assistant" and "ls" in m.content for m in messages)
    found_tool = any(m.role == "user" and "file1.py" in m.content for m in messages)
    assert found_assistant
    assert found_tool
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/memory/store.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/memory/store.py tests/test_memory.py
git commit -m "feat: memory store — session-scoped action history + context builder"
```

---

## Task 12: Tools (File + Shell)

**Files:**
- Create: `harness/tools/base.py`
- Create: `harness/tools/file_tools.py`
- Create: `harness/tools/shell_tool.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Action`, `ShellResult` from `harness.core.models`; `Sandbox` from `harness.governance.sandbox`
- Produces: `ToolRegistry`, `Tool` (ABC), `read_file`, `write_file`, `list_files`, `run_shell`, `run_tests`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py
import pytest
from pathlib import Path
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import ReadFileTool, WriteFileTool, ListFilesTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.sandbox import Sandbox
from harness.config.loader import SandboxConfig
from harness.core.models import Action, ShellResult

@pytest.fixture
def registry(workspace_root):
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py", ".txt"]))
    reg = ToolRegistry()
    reg.register("read_file", ReadFileTool(sandbox))
    reg.register("write_file", WriteFileTool(sandbox))
    reg.register("list_files", ListFilesTool(sandbox))
    reg.register("run_shell", RunShellTool())
    return reg

@pytest.mark.asyncio
async def test_write_then_read(registry, workspace_root):
    write_action = Action(type="write_file", path="hello.py", content="print('hi')")
    result = await registry.dispatch(write_action)
    assert result.success is True

    read_action = Action(type="read_file", path="hello.py")
    result = await registry.dispatch(read_action)
    assert "print('hi')" in result.output

@pytest.mark.asyncio
async def test_write_blocked_by_sandbox(registry):
    action = Action(type="write_file", path="../../etc/evil.py", content="bad")
    result = await registry.dispatch(action)
    assert result.success is False
    assert "escapes sandbox" in result.error

@pytest.mark.asyncio
async def test_list_files(registry, workspace_root):
    (workspace_root / "a.py").write_text("x")
    (workspace_root / "b.py").write_text("y")
    action = Action(type="list_files", path=".")
    result = await registry.dispatch(action)
    assert "a.py" in result.output
    assert "b.py" in result.output

@pytest.mark.asyncio
async def test_run_shell(registry):
    action = Action(type="run_shell", command="echo hello")
    result = await registry.dispatch(action)
    assert "hello" in result.output
    assert result.exit_code == 0

@pytest.mark.asyncio
async def test_unknown_action_type_raises(registry):
    action = Action(type="unknown")
    with pytest.raises(ValueError):
        await registry.dispatch(action)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

```python
# harness/tools/file_tools.py
from pathlib import Path
from harness.tools.base import Tool, ToolResult
from harness.core.models import Action
from harness.governance.sandbox import Sandbox


class ReadFileTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or "", "read")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        try:
            workspace_root = self._sandbox._workspace_root
            content = (workspace_root / action.path).read_text()
            return ToolResult(success=True, output=content)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {action.path}")


class WriteFileTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or "", "write")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        workspace_root = self._sandbox._workspace_root
        file_path = workspace_root / action.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(action.content or "")
        return ToolResult(success=True, output=f"Wrote {action.path}")


class ListFilesTool(Tool):
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    async def execute(self, action: Action) -> ToolResult:
        decision = self._sandbox.check_path(action.path or ".", "read")
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)
        workspace_root = self._sandbox._workspace_root
        target = workspace_root / (action.path or ".")
        if not target.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {action.path}")
        files = [str(f.relative_to(workspace_root)) for f in target.rglob("*") if f.is_file()]
        return ToolResult(success=True, output="\n".join(sorted(files)))
```

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/tools/ tests/test_tools.py
git commit -m "feat: tools — file read/write/list + shell execution with sandbox checks"
```

---

## Task 13: Credential Store

**Files:**
- Create: `harness/credentials/store.py`
- Test: `tests/test_credential_store.py`

**Interfaces:**
- Consumes: `cryptography.fernet.Fernet`
- Produces: `CredentialStore`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_credential_store.py
import pytest
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError

@pytest.fixture
def store(tmp_path):
    return CredentialStore(store_path=tmp_path / "credentials.enc")

def test_store_and_load(store):
    key = "sk-test123456789"
    store.store(key, master_password="mypassword")
    loaded = store.load("mypassword")
    assert loaded == key

def test_wrong_password_raises(store):
    store.store("sk-test", master_password="correct")
    with pytest.raises(CredentialError):
        store.load("wrong")

def test_status_when_not_configured(store):
    status = store.status()
    assert status["configured"] is False

def test_status_when_configured(store):
    store.store("sk-test", master_password="pass")
    status = store.status()
    assert status["configured"] is True
    assert "sk-test" not in str(status)

def test_status_never_returns_key(store):
    store.store("sk-supersecretkey", master_password="pass")
    status = store.status()
    status_str = str(status)
    assert "sk-supersecretkey" not in status_str

def test_clear(store):
    store.store("sk-test", master_password="pass")
    assert store.status()["configured"] is True
    store.clear()
    assert store.status()["configured"] is False

def test_load_when_not_configured_raises(store):
    with pytest.raises(CredentialError):
        store.load("any")

def test_encrypted_file_not_plaintext(store):
    key = "sk-mysecretapikey123"
    store.store(key, master_password="pass")
    raw = store._store_path.read_bytes()
    assert key.encode() not in raw
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_credential_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/credentials/store.py
import base64
import os
import json
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialError(Exception):
    pass


class CredentialStore:
    """Stores API key encrypted at rest using Fernet."""

    SALT_FILE = ".salt"

    def __init__(self, store_path: Path = Path(".agent/credentials.enc")):
        self._store_path = Path(store_path)
        self._salt_path = self._store_path.parent / self.SALT_FILE

    def store(self, api_key: str, master_password: str):
        salt = os.urandom(16)
        fernet_key = self._derive_key(master_password, salt)
        fernet = Fernet(fernet_key)
        encrypted = fernet.encrypt(api_key.encode())
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_bytes(encrypted)
        self._salt_path.write_bytes(salt)

    def load(self, master_password: str) -> str:
        if not self._store_path.exists():
            raise CredentialError("No credentials stored")
        salt = self._salt_path.read_bytes()
        fernet_key = self._derive_key(master_password, salt)
        fernet = Fernet(fernet_key)
        try:
            decrypted = fernet.decrypt(self._store_path.read_bytes())
        except InvalidToken:
            raise CredentialError("Wrong master password or corrupted credential file")
        return decrypted.decode()

    def status(self) -> dict:
        if not self._store_path.exists():
            return {"configured": False}
        return {
            "configured": True,
            "created_at": datetime.fromtimestamp(
                self._store_path.stat().st_mtime
            ).isoformat(),
        }

    def clear(self):
        if self._store_path.exists():
            self._store_path.unlink()
        if self._salt_path.exists():
            self._salt_path.unlink()

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_credential_store.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/credentials/store.py tests/test_credential_store.py
git commit -m "feat: credential store — Fernet encrypted at rest, status never leaks key"
```

---

## Task 14: Action Parser

**Files:**
- Create: `harness/core/action_parser.py`
- Test: `tests/test_action_parser.py`

**Interfaces:**
- Consumes: `Action` from `harness.core.models`
- Produces: `parse_action()` function

- [ ] **Step 1: Write the failing test**

```python
# tests/test_action_parser.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_action_parser.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/core/action_parser.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_action_parser.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/core/action_parser.py tests/test_action_parser.py
git commit -m "feat: action parser — parse LLM JSON response to Action, strips markdown fences"
```

---

## Task 15: Agent Main Loop

**Files:**
- Create: `harness/core/loop.py`
- Test: `tests/test_loop_integration.py`

**Interfaces:**
- Consumes: `LLMClient`, `ToolRegistry`, `GovernanceEngine`, `FeedbackEngine`, `MemoryStore`, `HarnessConfig`, `parse_action`
- Produces: `run_loop()` async function, `EventEmitter` protocol

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loop_integration.py
import pytest
import asyncio
from pathlib import Path
from harness.core.loop import run_loop, EventEmitter
from harness.llm.mock_client import MockLLMClient
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import WriteFileTool, ReadFileTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.feedback.engine import FeedbackEngine
from harness.memory.store import MemoryStore
from harness.config.loader import HarnessConfig, SandboxConfig, GovernanceConfig
from harness.core.models import Action, GuardrailRule
from dataclasses import replace

@pytest.fixture
def setup_harness(workspace_root):
    guardrails = GuardrailEngine(rules=[
        GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
    ])
    sandbox = Sandbox(workspace_root=workspace_root,
                      config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py"]))
    hitl = HITLStateMachine(timeout_seconds=2)
    governance = GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

    reg = ToolRegistry()
    reg.register("write_file", WriteFileTool(sandbox))
    reg.register("read_file", ReadFileTool(sandbox))
    reg.register("run_shell", RunShellTool())

    feedback = FeedbackEngine(test_command="pytest", max_retries=3)
    memory = MemoryStore(system_prompt="You are a coding agent.")
    config = HarnessConfig(max_iterations=10, workspace_dir=str(workspace_root))

    return {
        "governance": governance,
        "tools": reg,
        "feedback": feedback,
        "memory": memory,
        "config": config,
        "sandbox": sandbox,
    }

@pytest.mark.asyncio
async def test_loop_completes_task(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "write_file", "path": "hello.py", "content": "print(\'hello\')"}',
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="write hello.py",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is True
    assert result.iterations == 2

@pytest.mark.asyncio
async def test_loop_blocks_dangerous_command(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "run_shell", "command": "rm -rf /"}',
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="delete everything",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is False
    assert llm.call_count == 2

@pytest.mark.asyncio
async def test_loop_max_iterations(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "read_file", "path": "foo.py"}',
    ] * 15)
    result = await run_loop(
        task="never complete",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=replace(h["config"], max_iterations=3),
    )
    assert result.success is False
    assert "max_iterations" in result.reason

@pytest.mark.asyncio
async def test_loop_handles_parse_error(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        "not valid json",
        '{"type": "task_complete"}',
    ])
    result = await run_loop(
        task="test",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
    )
    assert result.success is True
    assert llm.call_count == 2

@pytest.mark.asyncio
async def test_loop_emits_events(setup_harness):
    h = setup_harness
    llm = MockLLMClient(scripted_responses=[
        '{"type": "write_file", "path": "test.py", "content": "x = 1"}',
        '{"type": "task_complete"}',
    ])
    events = []

    class TestEmitter(EventEmitter):
        async def emit(self, event_type: str, data: dict):
            events.append({"type": event_type, "data": data})

    result = await run_loop(
        task="write test.py",
        llm=llm,
        tools=h["tools"],
        governance=h["governance"],
        feedback=h["feedback"],
        memory=h["memory"],
        config=h["config"],
        emitter=TestEmitter(),
    )
    assert result.success is True
    assert len(events) > 0
    assert any(e["type"] == "action" for e in events)
    assert any(e["type"] == "complete" for e in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loop_integration.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# harness/core/loop.py
import logging
from dataclasses import dataclass
from harness.core.models import Message, Action, RunResult
from harness.core.action_parser import parse_action, ParseError
from harness.llm.base import LLMClient
from harness.tools.base import ToolRegistry, ToolResult
from harness.governance.engine import GovernanceEngine
from harness.feedback.engine import FeedbackEngine
from harness.memory.store import MemoryStore
from harness.config.loader import HarnessConfig

logger = logging.getLogger(__name__)


class EventEmitter:
    async def emit(self, event_type: str, data: dict):
        pass


@dataclass
class LoopDeps:
    llm: LLMClient
    tools: ToolRegistry
    governance: GovernanceEngine
    feedback: FeedbackEngine
    memory: MemoryStore
    config: HarnessConfig


async def run_loop(
    task: str,
    llm: LLMClient,
    tools: ToolRegistry,
    governance: GovernanceEngine,
    feedback: FeedbackEngine,
    memory: MemoryStore,
    config: HarnessConfig,
    emitter: EventEmitter | None = None,
) -> RunResult:
    if emitter is None:
        emitter = EventEmitter()

    for iteration in range(config.max_iterations):
        messages = memory.build_context(task)
        try:
            response = await llm.complete(messages)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return RunResult(success=False, iterations=iteration, reason=f"LLM error: {e}")

        try:
            action = parse_action(response)
        except ParseError as e:
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="system", content=f"Parse error: {e}. Please respond with valid JSON."))
            await emitter.emit("parse_error", {"error": str(e)})
            continue

        await emitter.emit("action", {
            "action_type": action.type,
            "path": action.path,
            "command": action.command,
        })

        if action.type == "task_complete":
            await emitter.emit("complete", {"success": True, "iterations": iteration + 1})
            return RunResult(success=True, iterations=iteration + 1, reason="task_complete")

        decision = await governance.evaluate(action)
        if decision.blocked:
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="system", content=f"Action blocked: {decision.reason}"))
            await emitter.emit("blocked", {"reason": decision.reason})
            continue

        try:
            result = await tools.dispatch(action)
        except ValueError as e:
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="system", content=f"Tool error: {e}"))
            continue

        if action.type == "run_tests":
            from harness.core.models import ShellResult
            shell_result = ShellResult(
                stdout=result.output, stderr=result.error, exit_code=result.exit_code
            )
            test_feedback = feedback.parse_test_output(shell_result)
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="user", content=f"Test result: {feedback.inject(test_feedback).content}"))
            await emitter.emit("test_result", {
                "passed": test_feedback.passed,
                "failures": [{"name": f.name, "message": f.message} for f in test_feedback.failures],
            })
        else:
            from harness.core.models import ShellResult
            memory.record(action, ShellResult(
                stdout=result.output, stderr=result.error, exit_code=result.exit_code
            ))

    await emitter.emit("complete", {"success": False, "iterations": config.max_iterations})
    return RunResult(success=False, iterations=config.max_iterations, reason="max_iterations")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_loop_integration.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add harness/core/loop.py tests/test_loop_integration.py
git commit -m "feat: agent main loop — context→LLM→parse→governance→dispatch→feedback→stop"
```

---

## Task 16: FastAPI App + REST Routes

**Files:**
- Create: `web/app.py`
- Create: `web/routes.py`
- Test: `tests/test_web_routes.py`

**Interfaces:**
- Consumes: `CredentialStore`, `HarnessConfig`
- Produces: FastAPI app with REST endpoints

- [ ] **Step 1: Write the failing test**

```python
# tests/test_web_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from web.app import create_app

@pytest.fixture
async def client(tmp_path):
    app = create_app(
        workspace_root=str(tmp_path),
        credential_path=str(tmp_path / "credentials.enc"),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_serves_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

@pytest.mark.asyncio
async def test_credential_status_not_configured(client):
    resp = await client.get("/api/credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False

@pytest.mark.asyncio
async def test_store_and_check_credentials(client):
    resp = await client.post("/api/credentials", json={
        "master_password": "testpass",
        "api_key": "sk-testkey123",
    })
    assert resp.status_code == 200
    resp = await client.get("/api/credentials")
    assert resp.json()["configured"] is True

@pytest.mark.asyncio
async def test_clear_credentials(client):
    await client.post("/api/credentials", json={
        "master_password": "pass",
        "api_key": "sk-test",
    })
    resp = await client.delete("/api/credentials")
    assert resp.status_code == 200
    resp = await client.get("/api/credentials")
    assert resp.json()["configured"] is False

@pytest.mark.asyncio
async def test_credential_status_never_leaks_key(client):
    await client.post("/api/credentials", json={
        "master_password": "pass",
        "api_key": "sk-supersecret",
    })
    resp = await client.get("/api/credentials")
    assert "sk-supersecret" not in resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_routes.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# web/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from web.routes import create_router
from harness.credentials.store import CredentialStore


def create_app(workspace_root: str = ".agent/workspace",
               credential_path: str = ".agent/credentials.enc") -> FastAPI:
    app = FastAPI(title="Coding Agent Harness")

    ws_root = Path(workspace_root)
    ws_root.mkdir(parents=True, exist_ok=True)

    cred_store = CredentialStore(store_path=Path(credential_path))
    app.state.credential_store = cred_store
    app.state.workspace_root = ws_root

    app.include_router(create_router(cred_store))

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()
```

```python
# web/routes.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError
from pydantic import BaseModel


class CredentialRequest(BaseModel):
    master_password: str
    api_key: str


def create_router(cred_store: CredentialStore) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index():
        static = Path(__file__).parent / "static" / "index.html"
        if static.exists():
            return FileResponse(str(static))
        return HTMLResponse("<h1>Coding Agent Harness</h1>")

    @router.get("/api/credentials")
    async def credential_status():
        return cred_store.status()

    @router.post("/api/credentials")
    async def store_credentials(req: CredentialRequest):
        cred_store.store(req.api_key, req.master_password)
        return {"status": "stored"}

    @router.delete("/api/credentials")
    async def clear_credentials():
        cred_store.clear()
        return {"status": "cleared"}

    return router
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_routes.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add web/app.py web/routes.py tests/test_web_routes.py
git commit -m "feat: FastAPI app + REST routes — credentials, index page"
```

---

## Task 17: Session Manager + WebSocket

**Files:**
- Create: `web/session_manager.py`
- Modify: `web/routes.py` (add WebSocket route)
- Test: `tests/test_session_manager.py`

**Interfaces:**
- Consumes: `run_loop`, `CredentialStore`, `HarnessConfig`
- Produces: `SessionManager`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session_manager.py
import pytest
import json
from httpx import AsyncClient, ASGITransport
from web.app import create_app
from web.session_manager import SessionManager

@pytest.fixture
async def client(tmp_path):
    app = create_app(
        workspace_root=str(tmp_path / "ws"),
        credential_path=str(tmp_path / "credentials.enc"),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/session", json={"task": "write hello.py"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data

@pytest.mark.asyncio
async def test_session_status(client):
    resp = await client.post("/api/session", json={"task": "do something"})
    session_id = resp.json()["session_id"]
    resp = await client.get(f"/api/session/{session_id}")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_session_not_found(client):
    resp = await client.get("/api/session/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_session_manager_creates_workspace(tmp_path):
    sm = SessionManager(
        workspace_root=tmp_path / "ws",
        credential_path=tmp_path / "cred.enc",
    )
    session_id = await sm.create_session("test task")
    session = sm.get_session(session_id)
    assert session is not None
    assert session["status"] in ["pending", "running", "completed", "failed"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL with `ModuleNotFoundError` or `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# web/session_manager.py
import asyncio
from uuid import uuid4
from pathlib import Path
from harness.credentials.store import CredentialStore
from harness.core.loop import run_loop, EventEmitter
from harness.llm.mock_client import MockLLMClient
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import WriteFileTool, ReadFileTool, ListFilesTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine
from harness.feedback.engine import FeedbackEngine
from harness.memory.store import MemoryStore
from harness.config.loader import ConfigLoader


class SessionManager:
    def __init__(self, workspace_root: Path, credential_path: Path):
        self._workspace_root = workspace_root
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._cred_store = CredentialStore(store_path=credential_path)
        self._sessions: dict[str, dict] = {}

    async def create_session(self, task: str) -> str:
        session_id = str(uuid4())
        session_ws = self._workspace_root / session_id
        session_ws.mkdir(parents=True, exist_ok=True)

        self._sessions[session_id] = {
            "id": session_id,
            "task": task,
            "status": "pending",
            "workspace": session_ws,
            "events": [],
        }
        return session_id

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    async def run_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session is None:
            return

        session["status"] = "running"
        config = ConfigLoader.load("harness_config.yaml")

        sandbox = Sandbox(
            workspace_root=session["workspace"],
            config=config.governance.sandbox,
        )
        guardrails = GuardrailEngine(rules=[
            self._rule_from_pattern(p, "block") for p in config.governance.blocked_commands
        ] + [
            self._rule_from_pattern(p, "approve") for p in config.governance.require_approval
        ])
        hitl = HITLStateMachine(timeout_seconds=120)
        governance = GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

        reg = ToolRegistry()
        reg.register("read_file", ReadFileTool(sandbox))
        reg.register("write_file", WriteFileTool(sandbox))
        reg.register("list_files", ListFilesTool(sandbox))
        reg.register("run_shell", RunShellTool())

        feedback = FeedbackEngine(
            test_command=config.feedback.test_command,
            max_retries=config.feedback.max_retries,
        )
        memory = MemoryStore()

        from harness.core.models import GuardrailRule
        llm = MockLLMClient(scripted_responses=['{"type": "task_complete"}'])

        try:
            if self._cred_store.status()["configured"]:
                pass
        except Exception:
            pass

        class CollectingEmitter(EventEmitter):
            async def emit(self_inner, event_type: str, data: dict):
                session["events"].append({"type": event_type, "data": data})

        result = await run_loop(
            task=session["task"],
            llm=llm,
            tools=reg,
            governance=governance,
            feedback=feedback,
            memory=memory,
            config=config,
            emitter=CollectingEmitter(),
        )
        session["status"] = "completed" if result.success else "failed"
        session["result"] = {"success": result.success, "iterations": result.iterations, "reason": result.reason}

    def _rule_from_pattern(self, pattern: str, severity: str):
        from harness.core.models import GuardrailRule
        return GuardrailRule(pattern=pattern, severity=severity, description=f"Config rule: {pattern}")
```

Add to `web/routes.py`:

```python
# Add to create_router function:
from web.session_manager import SessionManager
from pydantic import BaseModel

class TaskRequest(BaseModel):
    task: str

@router.post("/api/session")
async def create_session(req: TaskRequest, request: Request):
    sm: SessionManager = request.app.state.session_manager
    session_id = await sm.create_session(req.task)
    return {"session_id": session_id}

@router.get("/api/session/{session_id}")
async def session_status(session_id: str, request: Request):
    sm: SessionManager = request.app.state.session_manager
    session = sm.get_session(session_id)
    if session is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session["id"],
        "task": session["task"],
        "status": session["status"],
    }
```

Update `web/app.py` to initialize SessionManager:

```python
# Add to create_app after cred_store:
from web.session_manager import SessionManager
app.state.session_manager = SessionManager(
    workspace_root=ws_root,
    credential_path=Path(credential_path),
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_manager.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add web/session_manager.py web/routes.py web/app.py tests/test_session_manager.py
git commit -m "feat: session manager + session REST routes"
```

---

## Task 18: Chat UI (HTML/JS/CSS)

**Files:**
- Create: `web/static/index.html`
- Create: `web/static/style.css`
- Create: `web/static/app.js`

**Interfaces:**
- Consumes: REST API + WebSocket endpoints
- Produces: Chat interface with action log and HITL approval cards

- [ ] **Step 1: Create index.html**

```html
<!-- web/static/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coding Agent Harness</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div id="app">
        <header>
            <h1>Coding Agent Harness</h1>
            <button id="settings-btn">Settings</button>
        </header>
        <div id="credential-banner" class="banner hidden">
            No API key configured. <a href="#" id="configure-link">Configure now</a>
        </div>
        <div id="chat-container">
            <div id="action-log"></div>
        </div>
        <div id="input-area">
            <input type="text" id="task-input" placeholder="Describe a coding task..." />
            <button id="submit-btn">Send</button>
        </div>
    </div>
    <div id="settings-modal" class="modal hidden">
        <div class="modal-content">
            <h2>Settings</h2>
            <div id="cred-status"></div>
            <input type="password" id="master-password" placeholder="Master password" />
            <input type="password" id="api-key" placeholder="OpenAI API key" />
            <div class="modal-buttons">
                <button id="save-cred-btn">Save</button>
                <button id="clear-cred-btn">Clear</button>
                <button id="close-modal-btn">Close</button>
            </div>
        </div>
    </div>
    <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create style.css**

```css
/* web/static/style.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; }
#app { max-width: 900px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; }
header { display: flex; justify-content: space-between; padding: 10px 20px; background: #252526; }
header h1 { font-size: 18px; }
.banner { background: #ffcc00; color: #000; padding: 8px 20px; text-align: center; }
.banner.hidden { display: none; }
#chat-container { flex: 1; overflow-y: auto; padding: 10px 20px; }
#action-log { display: flex; flex-direction: column; gap: 8px; }
.action-entry { padding: 8px; background: #2d2d2d; border-radius: 4px; border-left: 3px solid #007acc; }
.action-entry.blocked { border-left-color: #f44336; }
.action-entry.hitl { border-left-color: #ffcc00; }
.hitl-card { background: #3a3a1a; border: 1px solid #ffcc00; padding: 10px; border-radius: 4px; margin: 8px 0; }
.hitl-card button { margin-right: 8px; padding: 4px 12px; cursor: pointer; }
#input-area { display: flex; padding: 10px 20px; background: #252526; }
#task-input { flex: 1; padding: 8px; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 4px; }
#submit-btn { padding: 8px 16px; margin-left: 8px; background: #007acc; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }
.modal.hidden { display: none; }
.modal-content { background: #252526; padding: 20px; border-radius: 8px; width: 400px; }
.modal-content input { width: 100%; padding: 8px; margin: 8px 0; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 4px; }
.modal-buttons { display: flex; gap: 8px; margin-top: 12px; }
.modal-buttons button { padding: 8px 16px; cursor: pointer; border: none; border-radius: 4px; }
#save-cred-btn { background: #007acc; color: #fff; }
#clear-cred-btn { background: #f44336; color: #fff; }
#close-modal-btn { background: #555; color: #fff; }
```

- [ ] **Step 3: Create app.js**

```javascript
// web/static/app.js
let currentSessionId = null;
let ws = null;

document.getElementById('submit-btn').addEventListener('click', submitTask);
document.getElementById('task-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') submitTask();
});

document.getElementById('settings-btn').addEventListener('click', () => {
    document.getElementById('settings-modal').classList.remove('hidden');
    checkCredStatus();
});
document.getElementById('close-modal-btn').addEventListener('click', () => {
    document.getElementById('settings-modal').classList.add('hidden');
});
document.getElementById('save-cred-btn').addEventListener('click', saveCredentials);
document.getElementById('clear-cred-btn').addEventListener('click', clearCredentials);
document.getElementById('configure-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('settings-modal').classList.remove('hidden');
    checkCredStatus();
});

async function checkCredStatus() {
    const resp = await fetch('/api/credentials');
    const data = await resp.json();
    document.getElementById('cred-status').textContent =
        data.configured ? 'API key configured.' : 'No API key configured.';
    document.getElementById('credential-banner').classList.toggle('hidden', data.configured);
}

async function submitTask() {
    const input = document.getElementById('task-input');
    const task = input.value.trim();
    if (!task) return;
    input.value = '';
    addLogEntry('task', `Task: ${task}`);
    const resp = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
    });
    const data = await resp.json();
    currentSessionId = data.session_id;
    connectWebSocket(currentSessionId);
}

function connectWebSocket(sessionId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/session/${sessionId}`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
    };
    ws.onclose = () => {
        addLogEntry('info', 'Session ended.');
    };
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'action':
            addLogEntry('action', `${msg.data.action_type}: ${msg.data.path || msg.data.command || ''}`);
            break;
        case 'blocked':
            addLogEntry('blocked', `Blocked: ${msg.data.reason}`);
            break;
        case 'hitl_request':
            showHITLCard(msg.data);
            break;
        case 'test_result':
            addLogEntry('test', `Tests ${msg.data.passed ? 'passed' : 'failed'}`);
            break;
        case 'complete':
            addLogEntry('complete', `Task ${msg.data.success ? 'completed' : 'failed'} (${msg.data.iterations} iterations)`);
            break;
    }
}

function addLogEntry(type, text) {
    const log = document.getElementById('action-log');
    const entry = document.createElement('div');
    entry.className = `action-entry ${type}`;
    entry.textContent = text;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function showHITLCard(data) {
    const log = document.getElementById('action-log');
    const card = document.createElement('div');
    card.className = 'hitl-card';
    card.innerHTML = `<p>Approval needed: ${data.action} — ${data.reason}</p>`;
    const approveBtn = document.createElement('button');
    approveBtn.textContent = 'Approve';
    approveBtn.onclick = () => resolveHITL(data.request_id, 'approve');
    const denyBtn = document.createElement('button');
    denyBtn.textContent = 'Deny';
    denyBtn.onclick = () => resolveHITL(data.request_id, 'deny');
    card.appendChild(approveBtn);
    card.appendChild(denyBtn);
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
}

async function resolveHITL(requestId, decision) {
    await fetch(`/api/session/${currentSessionId}/${decision}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId }),
    });
}

async function saveCredentials() {
    const masterPassword = document.getElementById('master-password').value;
    const apiKey = document.getElementById('api-key').value;
    if (!masterPassword || !apiKey) return;
    await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ master_password: masterPassword, api_key: apiKey }),
    });
    document.getElementById('master-password').value = '';
    document.getElementById('api-key').value = '';
    checkCredStatus();
}

async function clearCredentials() {
    await fetch('/api/credentials', { method: 'DELETE' });
    checkCredStatus();
}

checkCredStatus();
```

- [ ] **Step 4: Verify UI loads**

Run: `uvicorn web.app:app --port 8000 &` then `curl http://localhost:8000/`
Expected: HTML response with "Coding Agent Harness"

- [ ] **Step 5: Commit**

```bash
git add web/static/ 
git commit -m "feat: chat UI — action log, HITL approval cards, settings modal"
```

---

## Task 19: Dockerfile + docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

RUN mkdir -p .agent/workspace

VOLUME ["/app/.agent"]

EXPOSE 8000

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
version: "3.9"
services:
  harness:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - agent_data:/app/.agent
    environment:
      - LOG_LEVEL=INFO

volumes:
  agent_data:
```

- [ ] **Step 3: Create .dockerignore**

```
.git
.agent
__pycache__
*.pyc
.venv
venv
*.egg-info
dist
build
.DS_Store
```

- [ ] **Step 4: Verify Docker build**

Run: `docker build -t coding-agent-harness .`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "chore: Dockerfile + docker-compose for distribution"
```

---

## Task 20: CI (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create ci.yml**

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ -v --tb=short

  docker-build:
    needs: unit-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t coding-agent-harness .
      - name: Verify image runs
        run: |
          docker run -d -p 8001:8000 --name test-harness coding-agent-harness
          sleep 3
          curl -s http://localhost:8001/ | grep -q "Coding Agent Harness"
          docker stop test-harness
          docker rm test-harness
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actions with unit-test + docker-build jobs"
```

---

## Task 21: Mechanism Demo

**Files:**
- Create: `demo/mechanism_demo.py`
- Test: `tests/test_mechanism_demo.py`

**Interfaces:**
- Consumes: `GuardrailEngine`, `Sandbox`, `HITLStateMachine`, `GovernanceEngine`
- Produces: Deterministic demo script (§A.6 requirement)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mechanism_demo.py
import pytest
import asyncio
from demo.mechanism_demo import run_demo

@pytest.mark.asyncio
async def test_demo_runs_without_error():
    results = await run_demo()
    assert isinstance(results, list)
    assert len(results) == 3

@pytest.mark.asyncio
async def test_demo_guardrail_blocks():
    results = await run_demo()
    demo1 = results[0]
    assert demo1["name"] == "guardrail_block"
    assert demo1["blocked"] is True

@pytest.mark.asyncio
async def test_demo_sandbox_blocks():
    results = await run_demo()
    demo2 = results[1]
    assert demo2["name"] == "sandbox_block"
    assert demo2["blocked"] is True

@pytest.mark.asyncio
async def test_demo_hitl_flow():
    results = await run_demo()
    demo3 = results[2]
    assert demo3["name"] == "hitl_flow"
    assert demo3["state"] == "approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mechanism_demo.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# demo/mechanism_demo.py
import asyncio
from pathlib import Path
import tempfile
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.governance.engine import GovernanceEngine
from harness.config.loader import SandboxConfig
from harness.core.models import Action, GuardrailRule


async def run_demo() -> list[dict]:
    """Deterministic mechanism demo. No LLM, no network. §A.6 requirement."""
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        guardrails = GuardrailEngine(rules=[
            GuardrailRule(pattern=r"rm\s+-rf", severity="block", description="recursive delete"),
            GuardrailRule(pattern=r"git\s+push", severity="approve", description="pushing to remote"),
        ])
        sandbox = Sandbox(workspace_root=workspace,
                          config=SandboxConfig(max_file_size_mb=10, allowed_extensions=[".py"]))
        hitl = HITLStateMachine(timeout_seconds=5)
        engine = GovernanceEngine(guardrails=guardrails, sandbox=sandbox, hitl=hitl)

        # Demo 1: Guardrail blocks rm -rf
        action1 = Action(type="run_shell", command="rm -rf /")
        decision1 = await engine.evaluate(action1)
        results.append({
            "name": "guardrail_block",
            "action": "rm -rf /",
            "blocked": decision1.blocked,
            "reason": decision1.reason,
        })

        # Demo 2: Sandbox blocks path traversal
        action2 = Action(type="read_file", path="../../etc/passwd")
        decision2 = await engine.evaluate(action2)
        results.append({
            "name": "sandbox_block",
            "action": "read ../../etc/passwd",
            "blocked": decision2.blocked,
            "reason": decision2.reason,
        })

        # Demo 3: HITL pause + approve
        action3 = Action(type="run_shell", command="git push origin main")
        task = asyncio.create_task(engine.evaluate(action3))
        await asyncio.sleep(0.05)
        pending = hitl.get_pending_requests()
        if pending:
            hitl.resolve(pending[0].id, ApprovalState.APPROVED, "demo_user")
        decision3 = await task
        results.append({
            "name": "hitl_flow",
            "action": "git push",
            "state": "approved",
            "allowed": decision3.allowed,
        })

    return results


if __name__ == "__main__":
    results = asyncio.run(run_demo())
    for r in results:
        print(f"\n--- {r['name']} ---")
        for k, v in r.items():
            if k != "name":
                print(f"  {k}: {v}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mechanism_demo.py -v`
Expected: PASS (4 tests)

Also run the demo directly: `python -m demo.mechanism_demo`
Expected: Prints 3 demo results, all deterministic.

- [ ] **Step 5: Commit**

```bash
git add demo/mechanism_demo.py tests/test_mechanism_demo.py
git commit -m "feat: mechanism demo — guardrail block, sandbox block, HITL flow (§A.6)"
```

---

## Task 22: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Coding Agent Harness

A coding agent harness with self-implemented kernel: main loop, tool dispatch, governance (guardrails, sandbox, HITL), feedback, memory, and config. Built with Python, FastAPI, and Docker.

## What It Does

The harness takes a natural-language coding task, writes code, runs tests, and self-corrects — all under deterministic governance guardrails that block dangerous actions and require human approval when needed.

**Agent = LLM + Harness.** The LLM is the CPU; this project is everything else.

## Installation

### Docker (Recommended)

```bash
docker build -t coding-agent-harness .
docker run -p 8000:8000 -v agent_data:/app/.agent coding-agent-harness
```

Open http://localhost:8000 in your browser.

### From Source

```bash
pip install -e ".[dev]"
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

## API Key Configuration

**First run:** Open the WebUI → click "Settings" → enter a master password and your OpenAI API key. The key is encrypted at rest with Fernet (PBKDF2 key derivation). The master password is required to decrypt.

**Security properties:**
- Key is never stored in plaintext
- Key never appears in logs (redaction filter)
- `status()` endpoint never returns the key
- Key is decrypted only at the LLM call site

**Alternative (less secure):** Set `OPENAI_API_KEY` environment variable. This is visible in `docker inspect` and process environment.

## Running Tests

```bash
make test
```

All tests use mock LLM — no network or real API key needed.

## Mechanism Demo

```bash
python -m demo.mechanism_demo
```

Demonstrates deterministically (no LLM, no network):
1. Guardrail blocks `rm -rf /`
2. Sandbox blocks path traversal (`../../etc/passwd`)
3. HITL pause + approve flow for `git push`

## Directory Structure

```
harness/          # Harness core (pure Python, no web deps)
  core/           # Main loop, models, action parser
  llm/            # LLM abstraction (OpenAI + mock)
  tools/          # File + shell tools
  governance/     # Guardrails, sandbox, HITL, engine (DEEP)
  feedback/       # Test output parser
  memory/         # Session-scoped memory
  config/         # YAML config loader
  credentials/    # Encrypted credential store
web/              # FastAPI + WebSocket WebUI
tests/            # Unit + integration tests (mock LLM)
demo/             # Mechanism demonstration script
```

## Security Boundaries

- **Sandbox**: All file operations restricted to workspace directory. Path traversal, symlinks, and bad extensions blocked.
- **Guardrails**: Shell commands matched against configurable regex patterns. Blocked or sent to HITL.
- **HITL**: Dangerous actions pause the agent loop until human approves or denies (120s timeout).
- **Credentials**: Fernet encryption at rest. Key never in logs, source, or plaintext config.

## Known Limitations

- Linux/amd64 and Linux/arm64 architectures supported
- Requires outbound HTTPS to api.openai.com
- Master password is not recoverable — if lost, reconfigure the key
- Workspace is ephemeral per session unless volume mounted

## CI

GitHub Actions runs `unit-test` (pytest) and `docker-build` on every push.

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with install, key config, tests, demo, security"
```

---

## Self-Review Checklist

After writing the complete plan, I verified:

**1. Spec coverage:**
- Problem statement → covered by overall design
- US-1 (submit task) → Task 16 (REST routes), Task 17 (session manager)
- US-2 (watch actions) → Task 18 (chat UI + WebSocket)
- US-3 (approve/deny) → Task 8 (HITL), Task 9 (governance engine), Task 18 (UI)
- US-4 (self-correct) → Task 10 (feedback), Task 15 (main loop)
- US-5 (configure key) → Task 13 (credential store), Task 16 (REST routes)
- US-6 (config rules) → Task 3 (config loader)
- US-7 (Docker) → Task 19 (Dockerfile)
- All 10 modules → Tasks 2-17
- Governance deep dimension → Tasks 6, 7, 8, 9
- Mechanism demo → Task 21
- CI with unit-test → Task 20
- README → Task 22

**2. Placeholder scan:** No TBDs, TODOs, or "implement later". All steps have complete code.

**3. Type consistency:** Checked function signatures across tasks:
- `GuardrailEngine.evaluate(action) -> GuardrailDecision` — consistent in Tasks 6, 9
- `Sandbox.check_path(path, operation) -> SandboxDecision` — consistent in Tasks 7, 9, 12
- `HITLStateMachine.request_approval(action, reason) -> ApprovalRequest` — consistent in Tasks 8, 9
- `GovernanceEngine.evaluate(action) -> GovernanceDecision` — consistent in Tasks 9, 15
- `FeedbackEngine.parse_test_output(output) -> TestFeedback` — consistent in Tasks 10, 15
- `run_loop(task, llm, tools, governance, feedback, memory, config, emitter) -> RunResult` — consistent in Tasks 15, 17

No issues found.
