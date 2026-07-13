# SPEC.md — Coding Agent Harness

> Spec-Driven, Subagent-Built, Human-Owned.
>
> This document is the validated design produced through the Superpowers `brainstorming` skill. It serves as both the design doc (`docs/superpowers/specs/2026-07-10-coding-agent-harness-design.md`) and the project deliverable `SPEC.md` required by the AI4SE final project.

---

## 1. Problem Statement

### What problem are we solving?

When an LLM can write code, the real engineering challenge is not the code generation itself — it is the **harness**: the layer of engineering that wraps a raw LLM into a stable, reliable, safe system. A harness must organize context, dispatch tools, enforce governance, provide feedback, manage memory, and allow declarative configuration. Without these, an LLM is just a text generator that cannot safely act on the world.

This project builds a **Coding Agent Harness** — a system that takes a natural-language coding task, writes code, runs tests, and self-corrects, all under deterministic governance guardrails that prevent dangerous actions and require human approval when needed.

### Target users

- **Developers** who want to delegate coding tasks to an AI agent while maintaining control over what it can do.
- **AI4SE students** studying how agent harnesses work under the hood — the code is the textbook.

### Why is it worth building?

The core equation is **Agent = LLM + Harness**. The LLM is the CPU; the harness is everything else. This project makes the harness layer explicit, implemented in code (not prompts), and testable without a real LLM. It demonstrates that the engineering value — when LLMs can code — lives in governance, feedback, context management, and safety.

---

## 2. User Stories

All stories follow the INVEST principle (Independent, Negotiable, Valuable, Estimable, Small, Testable).

### US-1: Submit a coding task
**As a** developer,
**I want to** type a natural-language coding task in a web chat interface,
**So that** the agent starts working on it immediately.
- *Independent*: no dependency on other stories.
- *Testable*: POST `/api/session` with a task string returns a session ID.

### US-2: Watch the agent work in real-time
**As a** developer,
**I want to** see the agent's actions (file reads, writes, shell commands, test runs) stream live in the chat UI,
**So that** I know what the agent is doing at every step.
- *Testable*: WebSocket connection receives `action` events.

### US-3: Approve or deny dangerous actions
**As a** developer,
**I want to** be prompted to approve or deny actions the agent wants to take that are flagged as dangerous (e.g., `git push`, `pip install`, `rm`),
**So that** the agent cannot do anything harmful without my explicit consent.
- *Testable*: HITL state machine transitions PENDING → APPROVED/DENIED; agent loop pauses until resolved.

### US-4: Agent self-corrects from test failures
**As a** developer,
**I want to** the agent to run tests after writing code, and if tests fail, automatically read the failure messages and try to fix the code,
**So that** the agent converges on working code without manual intervention.
- *Testable*: Feedback engine parses pytest output, injects structured failure messages, agent's next action changes.

### US-5: Configure API key securely
**As a** developer,
**I want to** configure my OpenAI API key through a settings page with hidden input and a master password,
**So that** my key is never stored in plaintext, never appears in logs, and is encrypted at rest.
- *Testable*: Credential store encrypts/decrypts with Fernet; `status()` never returns the key.

### US-6: Configure governance rules declaratively
**As a** developer,
**I want to** edit a YAML config file to define which commands are blocked, which require approval, and which file paths are off-limits,
**So that** I can customize the agent's safety boundaries without modifying code.
- *Testable*: Config loader parses YAML; governance engine uses loaded rules; changing rules changes behavior.

### US-7: Run the harness in Docker
**As a** developer,
**I want to** start the entire system with a single `docker build && docker run` command,
**So that** I can deploy it on any machine without worrying about dependencies.
- *Testable*: Dockerfile builds; container starts; WebUI is accessible on port 8000.

---

## 3. Functional Specification

### Module 1: Agent Main Loop (`harness/core/loop.py`)

| Aspect | Description |
|--------|-------------|
| **Input** | Task string (natural language), LLM client, tool registry, governance engine, feedback engine, memory store, config |
| **Behavior** | Organizes context → calls LLM → parses response to Action → governance check → tool dispatch → feedback injection → memory record → stop check. Repeats up to `max_iterations`. |
| **Output** | `RunResult(success: bool, iterations: int, reason: str)` |
| **Boundary** | Stops at `max_iterations` (default 20). Stops when agent emits `task_complete` action. |
| **Error handling** | LLM errors → retry once, then fail. Parse errors → feed error back to LLM. Tool errors → feed error back to LLM. |

### Module 2: LLM Abstraction Layer (`harness/llm/`)

| Aspect | Description |
|--------|-------------|
| **Input** | List of `Message(role, content)` |
| **Behavior** | Calls the LLM provider's chat completions API, returns raw text response. |
| **Output** | Raw string (the LLM's response, which the loop parses into an Action) |
| **Boundary** | No tool calling / function calling — the harness parses the response itself. |
| **Error handling** | API errors → raise `LLMError` with status code and message. Rate limits → exponential backoff (3 retries). |
| **Mockability** | `MockLLMClient` takes scripted responses, asserts on message format. No network. |

### Module 3: Tools (`harness/tools/`)

| Tool | Input | Output | Governance check |
|------|-------|--------|-------------------|
| `read_file` | path | file contents (str) | Sandbox path check |
| `write_file` | path, content | success bool | Sandbox path + extension check |
| `list_files` | path | list of file paths | Sandbox path check |
| `run_shell` | command | ShellResult(stdout, stderr, exit_code) | Guardrail + HITL |
| `run_tests` | (none, uses config) | ShellResult | Wraps run_shell with the configured test command; loop parses output via FeedbackEngine |

### Module 4: Governance Engine (`harness/governance/`) — DEEP DIMENSION

| Sub-module | Input | Output | Description |
|------------|-------|--------|-------------|
| `GuardrailEngine` | Action | GuardrailDecision(allowed, requires_approval, reason) | Regex-based command pattern matching against config rules |
| `Sandbox` | path, operation | SandboxDecision(allowed, reason) | Path traversal check, extension whitelist, file size limit |
| `HITLStateMachine` | Action, reason | ApprovalRequest(state) | Async pause/resume via `asyncio.Event`; timeout after 120s |
| `GovernanceEngine` | Action | GovernanceDecision(allowed, blocked, reason) | Composes all three: sandbox → guardrail → HITL |

**Critical design property**: All four are pure functions or deterministic state machines. No LLM dependency. Unit-testable with constructed inputs.

### Module 5: Feedback Engine (`harness/feedback/`)

| Aspect | Description |
|--------|-------------|
| **Input** | ShellResult (from `run_tests` tool) |
| **Behavior** | Parses pytest output (`--tb=short` format), extracts failure names, messages, file paths, line numbers. |
| **Output** | `TestFeedback(passed: bool, failures: list[Failure], raw_output: str)` |
| **Boundary** | Truncates raw output to 2000 chars for context injection. Max 3 retry rounds. |
| **Error handling** | Unparseable output → returns `TestFeedback(passed=False, failures=[], raw_output=truncated)` |

### Module 6: Memory (`harness/memory/`)

| Aspect | Description |
|--------|-------------|
| **Input** | Action + Result (from each loop iteration) |
| **Behavior** | Stores action history in session scope. Builds context: system prompt + last N actions + task. |
| **Output** | `list[Message]` for LLM call |
| **Boundary** | Session-scoped only (no cross-session persistence). Last 10 actions kept in context. |
| **Error handling** | Empty memory → returns just system prompt + task. |

### Module 7: Config (`harness/config/`)

| Aspect | Description |
|--------|-------------|
| **Input** | YAML file path |
| **Behavior** | Parses YAML into `HarnessConfig` dataclass with nested governance, feedback, and general settings. |
| **Output** | `HarnessConfig` object |
| **Boundary** | Validates required fields. Falls back to defaults for missing optional fields. |
| **Error handling** | Missing file → use defaults. Invalid YAML → raise `ConfigError` with line number. |

### Module 8: Credential Store (`harness/credentials/`)

| Aspect | Description |
|--------|-------------|
| **Input** | Master password (for encrypt/decrypt), API key (for store) |
| **Behavior** | Encrypts API key with Fernet (key derived from master password via PBKDF2). Stores in `.agent/credentials.enc`. |
| **Output** | `load()` returns decrypted key string. `status()` returns `{"configured": bool}` — never the key. |
| **Boundary** | Key is decrypted only at LLM call site. Reference cleared after use. |
| **Error handling** | Wrong master password → `CredentialError`. Corrupted file → `CredentialError`. |

### Module 9: WebUI (`web/`)

| Aspect | Description |
|--------|-------------|
| **Input** | HTTP requests (REST) + WebSocket connections |
| **Behavior** | Serves chat UI. Manages sessions. Streams actions via WebSocket. Mediates HITL approvals. |
| **Output** | HTML page (GET `/`), JSON responses (REST), WebSocket events |
| **Boundary** | One session = one harness run. Multiple sessions can run concurrently. |
| **Error handling** | WebSocket disconnect → session continues, events buffered. Invalid session ID → 404. |

### Module 10: Session Manager (`web/session_manager.py`)

| Aspect | Description |
|--------|-------------|
| **Input** | Task string + WebSocket |
| **Behavior** | Creates harness instance, wires event emitter to WebSocket, starts `run_loop` as background task. |
| **Output** | Session ID (str) |
| **Boundary** | Each session has its own workspace subdirectory under `.agent/workspace/{session_id}/`. |
| **Error handling** | Harness crash → emit `error` event on WebSocket, mark session as failed. |

---

## 4. Non-Functional Requirements

### 4.1 Performance
- LLM call latency is the bottleneck (1-10s per call). Harness overhead < 100ms per iteration.
- WebSocket events delivered within 50ms of action execution.
- Support up to 5 concurrent sessions on a single container (sufficient for a demo/course project).

### 4.2 Security (Credential Threat Model)

| Threat | Vector | Mitigation |
|--------|--------|-----------|
| Key in source code | Git history | `.gitignore` for `.agent/`; pre-commit hook scanning for key patterns |
| Key in plaintext config | `.env` file | Encrypted file at rest (Fernet encryption) |
| Key in process environment | `export` in shell history | Key loaded via WebUI, not CLI export; if env var used, documented as less secure |
| Key in logs | Debug prints / error messages | Redaction filter on all loggers: `sk-***` pattern replaced with `sk-***REDACTED***` |
| Key in memory dump | Core dump / crash | Decrypt only at LLM call site; `del` reference after use; no long-lived storage |
| Key in Docker inspect | `docker inspect` shows env vars | Recommended: mount volume, configure via WebUI. Documented risk if env var used. |

### 4.3 Usability
- First-run: user sees clear "No API key configured" banner with a "Configure" button.
- Chat interface is self-explanatory: type task, press enter, watch actions stream.
- HITL approval cards are visually distinct (yellow border) and have clear Approve/Deny buttons.
- Settings page for credential management: store, update (overwrite), clear, check status.

### 4.4 Observability
- Every action logged with: timestamp, session ID, action type, action details, result, governance decision.
- Logs go to stdout (Docker-friendly) and `.agent/logs/{session_id}.jsonl` (structured).
- Log level configurable via env var `LOG_LEVEL` (default: INFO).
- Sensitive data (API keys, file contents with key patterns) redacted in logs.

---

## 5. System Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Container                       │
│                                                               │
│  ┌─────────────┐        WebSocket         ┌────────────────┐ │
│  │   Browser   │◄───────────────────────►│   FastAPI App   │ │
│  │  (Chat UI)  │  actions, HITL prompts  │  (uvicorn)      │ │
│  │             │  task submission        │                 │ │
│  └─────────────┘                         │  ┌───────────┐ │ │
│                                           │  │ API Routes │ │ │
│                                           │  │ + WS Mgr   │ │ │
│                                           │  └─────┬─────┘ │ │
│                                           │        │       │ │
│                                           │  ┌─────▼─────┐ │ │
│                                           │  │  Session   │ │ │
│                                           │  │  Manager   │ │ │
│                                           │  └─────┬─────┘ │ │
│                                           │        │       │ │
│                                           │  ┌─────▼─────┐ │ │
│                                           │  │  Harness   │ │ │
│                                           │  │   Core     │ │ │
│                                           │  │ (pure lib) │ │ │
│                                           │  └─────┬─────┘ │ │
│                                           └────────┼───────┘ │
│                                                    │         │
│  ┌─────────────────────────────────────────────────┘         │
│  │                                                            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  │   LLM    │  │  Tools   │  │Governance│  │ Feedback │ │
│  │  │ Abstract │  │ (file,   │  │ (rails,  │  │ (test    │ │
│  │  │ (OpenAI/ │  │  shell,  │  │  sandbox,│  │  runner, │ │
│  │  │  mock)   │  │  test)   │  │  HITL)   │  │  parser) │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│  │                                                            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐│
│  │  │  Memory  │  │  Config  │  │  Credential Store         ││
│  │  │ (session │  │ (YAML    │  │  (encrypted file,         ││
│  │  │  history)│  │  rules)  │  │   first-run guided entry) ││
│  │  └──────────┘  └──────────┘  └──────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Workspace (.agent/workspace/{session_id}/)              │ │
│  │  └── sandbox boundary for all file operations            │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │
         ▼ (outbound HTTPS)
   ┌──────────┐
   │ OpenAI   │
   │   API    │
   └──────────┘
```

### Data Flow

1. User types task in browser → POST `/api/session` → Session Manager creates harness instance → returns session ID
2. WebSocket connects to `/ws/session/{id}` → Session Manager starts `run_loop` as background task
3. **Each loop iteration**:
   - Memory builds context → LLM called → response parsed to Action
   - Governance evaluates Action → if blocked, feedback injected, loop continues
   - If HITL needed → WebSocket emits `hitl_request` → loop `await`s → user responds → loop resumes
   - Tool dispatched → result recorded in memory
   - If test run → feedback parsed → injected into next LLM call
   - WebSocket streams `action` event
   - Stop check: if `task_complete` → emit `complete` event, end loop
4. User can view action log, approve/deny HITL requests in real-time

### External Dependencies
- **OpenAI API** (chat completions) — the only external service dependency
- **PyPI packages**: `openai`, `fastapi`, `uvicorn`, `websockets`, `pyyaml`, `cryptography` (Fernet), `pytest`
- **Docker** (for distribution)
- **Render/Fly.io** (for cloud deployment, free tier)

---

## 6. Data Model

### Core Entities

```python
@dataclass
class Message:
    role: str          # "system" | "user" | "assistant"
    content: str       # message text

@dataclass
class Action:
    type: str          # "read_file" | "write_file" | "list_files" | "run_shell" | "run_tests" | "task_complete"
    path: str | None   # for file operations
    content: str | None # for write_file
    command: str | None # for run_shell

@dataclass
class ShellResult:
    stdout: str
    stderr: str
    exit_code: int

@dataclass
class Failure:
    name: str          # test name
    message: str       # failure message
    file: str          # source file
    line: int          # line number

@dataclass
class TestFeedback:
    passed: bool
    failures: list[Failure]
    raw_output: str

@dataclass
class GuardrailRule:
    pattern: str           # regex pattern to match against command
    severity: str          # "block" | "approve"
    description: str       # human-readable reason

@dataclass
class GuardrailDecision:
    allowed: bool
    requires_approval: bool
    reason: str
    rule: GuardrailRule | None

@dataclass
class SandboxDecision:
    allowed: bool
    reason: str

@dataclass
class ApprovalRequest:
    id: str
    action: Action
    reason: str
    state: str         # "pending" | "approved" | "denied" | "timeout"
    created_at: datetime
    decided_at: datetime | None
    decided_by: str | None

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

### Relationships
- `RunResult` ← produced by `run_loop` which processes `Action`s
- `Action` → evaluated by `GovernanceEngine` → produces `GovernanceDecision`
- `Action` (type=`run_tests`) → produces `ShellResult` → parsed by `FeedbackEngine` → `TestFeedback`
- `ApprovalRequest` ← created by `HITLStateMachine` when governance requires approval

### Constraints
- `Action.path` must resolve inside workspace root (enforced by Sandbox)
- `Action.command` must not match blocked patterns (enforced by GuardrailEngine)
- `ApprovalRequest.state` transitions: `pending` → `approved` | `denied` | `timeout` (one-way)
- `RunResult.iterations` ≤ `config.max_iterations`

---

## 7. Credential & Distribution Design

### 7.1 Credential Storage

**Method**: Encrypted file at rest using Fernet symmetric encryption.

- **Master password** → PBKDF2-HMAC-SHA256 (480k iterations) → Fernet key
- **API key** → encrypted with Fernet key → stored in `.agent/credentials.enc`
- **First-run**: WebUI settings page → hidden input for master password + API key → encrypt → store
- **Subsequent runs**: WebUI → enter master password → decrypt → key in memory for session
- **View status**: `{"configured": true, "created_at": "..."}` — never returns the key
- **Update**: overwrite the encrypted file (requires master password)
- **Clear**: delete the encrypted file

**Docker key configuration**:
- **Recommended**: Mount volume for `.agent/` → user configures key via WebUI on first run
- **Alternative**: `OPENAI_API_KEY` env var → documented as less secure (visible in `docker inspect`)

### 7.2 Distribution

**Form**: Docker container image.

- **Build**: `docker build -t coding-agent-harness .`
- **Run**: `docker run -p 8000:8000 -v agent_data:/app/.agent coding-agent-harness`
- **Registry**: Docker Hub or GitHub Container Registry (GHCR)
- **Key configuration on target machine**: Open WebUI at `http://localhost:8000` → Settings → enter master password + OpenAI key → encrypted and stored in the mounted volume

**Known limitations**:
- Linux/amd64 and Linux/arm64 architectures supported (multi-arch build in CI)
- Requires outbound HTTPS to `api.openai.com`
- Master password is not recoverable — if lost, user must reconfigure the key
- Workspace is ephemeral per session (not persisted across container restarts unless volume mounted)

---

## 8. Tech Selection & Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.12 | Rich LLM ecosystem, excellent test framework (pytest), natural async model for HITL, AI4SE course alignment |
| LLM provider | OpenAI (gpt-4o) | Most widely used, excellent Python SDK, well-documented API |
| Web framework | FastAPI + uvicorn | Async-native (WebSocket + HITL pause/resume), automatic API docs, lightweight |
| Frontend | Vanilla HTML/JS/CSS | No build step, lean Docker image, sufficient for chat UI |
| Testing | pytest + pytest-asyncio | Standard Python testing, async support for HITL tests |
| Credential encryption | cryptography (Fernet) | Standard library, AES-128-CBC + HMAC, well-audited |
| Config format | YAML | Human-readable, supports comments, standard for declarative config |
| Distribution | Docker | Single command build + run, portable, volume mount for credentials |
| CI | GitHub Actions | Free for public repos, Docker build support, required `unit-test` job |
| Cloud deployment | Render or Fly.io | Free tier, Docker support, automatic deploy from GitHub |

**No frontend framework** (Open Design) is used because this is a CLI/backend-focused project with a minimal WebUI. The project requirement for Open Design applies to frontend/UI projects; this project's UI is a thin chat wrapper, not a design-system-driven frontend. The UI is simple enough that vanilla HTML/JS/CSS is the right choice — adding a framework would add complexity without depth.

---

## 9. Domain & Mechanism Design (A.5 Extra Requirement)

### Domain: Coding

The coding domain has the clearest, most encodable mechanisms for an agent harness:

### Feedback Signals
- **What**: Running tests (pytest), linting (ruff/flake8), type checking (mypy)
- **Why objective**: Exit codes and structured output are deterministic — tests pass or fail, no ambiguity
- **How encoded**: `FeedbackEngine.parse_test_output()` is a pure function that parses pytest's `--tb=short` output into `TestFeedback(passed, failures[])`. No LLM judgment involved.

### Dangerous Actions
- **What**: Destructive shell commands (`rm -rf`, `sudo`), network operations (`curl | sh`, `git push`), package installation (`pip install`), file operations outside workspace
- **Why must intercept**: These can destroy data, exfiltrate secrets, or compromise the system
- **How encoded**: `GuardrailEngine` uses regex patterns from config to match commands. `Sandbox` checks path resolution against workspace boundary. `HITLStateMachine` pauses the loop for human approval. All deterministic, all unit-testable.

### Required Tools
- **What**: read_file, write_file, list_files, run_shell, run_tests
- **Why these**: They cover the minimum for a coding agent to read code, write code, see what files exist, run commands, and run tests
- **How encoded**: `ToolRegistry` dispatches by action type. Each tool is a function with governance checks baked in.

### Memory Needs
- **What**: Action history within a session (what the agent did, what results it got)
- **Why**: The LLM needs context of its previous actions to avoid repeating mistakes and to build on progress
- **How encoded**: `MemoryStore` records actions and results, builds context by assembling system prompt + last N actions + task. Session-scoped only (minimum implementation).

### Deep Dimension: Governance

**Why governance is the main contribution**:
1. It is the most code-heavy dimension — guardrails, sandbox, and HITL are all pure functions/state machines with zero LLM dependency
2. It directly addresses the project's core question: "when an LLM can act on the world, what prevents it from doing harm?"
3. It has the richest state machine (HITL: pending → approved/denied/timeout) which is interesting to implement and test
4. It is the dimension where "mechanism must be code, not prompts" is most clearly demonstrated — a prompt saying "don't run rm -rf" is unreliable; a `guardrail(action)` function is not

**How mechanisms are coded** (per §A.4):
- `GuardrailEngine.evaluate(action)` — regex pattern matching, returns `GuardrailDecision`. Test: `evaluate(Action(cmd="rm -rf /"))` → blocked. Deterministic.
- `Sandbox.check_path(path, op)` — path resolution + boundary check. Test: `check_path("../../etc/passwd", "read")` → blocked. Deterministic.
- `HITLStateMachine.request_approval(action)` — async pause via `asyncio.Event`, resume on `resolve()`. Test: create task, resolve as approved, assert state. Deterministic.
- `GovernanceEngine.evaluate(action)` — composes all three. Test: mock LLM tries `rm -rf`, governance blocks, loop continues. Deterministic.

**Judgment criterion (§A.4-C)**: Remove the real LLM, replace with `MockLLMClient`. All governance mechanisms still work and are unit-testable. The mock LLM can try to run `rm -rf /` — the guardrail blocks it every time, regardless of what the LLM "wants". This is the difference between a coded mechanism and a prompt.

---

## 10. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | User can submit a coding task via WebUI chat and receive a session ID | POST `/api/session` returns 200 with session ID |
| AC-2 | Agent actions stream in real-time via WebSocket | WebSocket receives `action` events within 100ms of execution |
| AC-3 | Guardrail blocks `rm -rf` command | Unit test: `evaluate(Action(cmd="rm -rf /"))` → `allowed=False` |
| AC-4 | Sandbox blocks path traversal (`../../etc/passwd`) | Unit test: `check_path("../../etc/passwd", "read")` → `allowed=False` |
| AC-5 | HITL pauses loop on dangerous action, resumes on approval | Unit test: mock LLM tries `git push`, HITL pauses, resolve as approved, loop continues |
| AC-6 | HITL denies action when user denies | Unit test: resolve as denied, loop feeds denial back to LLM |
| AC-7 | Feedback engine parses pytest failures | Unit test: parse sample pytest output → correct `TestFeedback` |
| AC-8 | Agent self-corrects from test failures | Integration test: mock LLM writes broken code, tests fail, feedback injected, mock LLM's next response is a fix |
| AC-9 | Credential store encrypts at rest | Unit test: store key, read encrypted file → not plaintext; load with correct password → correct key; load with wrong password → error |
| AC-10 | `status()` never returns the key | Unit test: `status()` output does not contain key string |
| AC-11 | Config loaded from YAML changes governance behavior | Unit test: add a blocked pattern to YAML, governance blocks matching command |
| AC-12 | `make test` runs all unit tests | `make test` exits 0 with all tests passing |
| AC-13 | Docker image builds and runs | `docker build` succeeds, `docker run` starts WebUI on port 8000 |
| AC-14 | Mechanism demo runs deterministically | Script demonstrates: guardrail block, HITL pause/resume, sandbox block — all without network or real LLM |
| AC-15 | CI pipeline has `unit-test` job that passes | GitHub Actions CI runs `unit-test` job, exits green |

---

## 11. Risks & Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM response parsing is fragile — LLM doesn't always return valid JSON | High | Medium | Use a simple, forgiving parser with fallback. Feed parse errors back to LLM with "your response was not valid, please use the format: {type, ...}". |
| OpenAI API rate limits during demo | Medium | High | Implement exponential backoff. Have a recorded demo as backup. |
| HITL timeout in async context causes deadlock | Low | High | Use `asyncio.wait_for` with explicit timeout. Unit test the timeout path. |
| Sandbox path resolution edge cases (symlinks, `..`, absolute paths) | Medium | High | Use `Path.resolve()` + `startswith()` check. Unit test all traversal vectors. |
| Docker multi-arch build fails on arm64 | Low | Low | CI builds both; if arm64 fails, document as amd64-only. |
| Cloud deployment free tier shuts down | Medium | Medium | Use Render/Fly.io free tier; keep container lightweight; have local Docker as fallback. |

### Open Questions

1. **Action format**: Should the LLM return JSON or a simpler format? JSON is standard but LLMs sometimes wrap it in markdown code blocks. Decision: use JSON with a forgiving parser that strips markdown fences.
2. **Workspace isolation**: Should each session get its own workspace subdirectory, or share one? Decision: per-session subdirectory (`.agent/workspace/{session_id}/`) for isolation.
3. **Test command**: Should the test command be configurable per-project or fixed? Decision: configurable in YAML (default: `pytest tests/ -v --tb=short`), but the workspace must contain the tests.
4. **HITL timeout**: What happens when the user doesn't respond? Decision: timeout after 120s, treat as denied, feed "approval timed out" back to LLM.

---

## Appendix: Project Structure

```
coding-agent-harness/
├── harness/                    # Harness core (pure Python library)
│   ├── __init__.py
│   ├── core/
│   │   ├── loop.py             # Agent main loop
│   │   └── action.py           # Action dataclass + parser
│   ├── llm/
│   │   ├── base.py             # LLMClient ABC
│   │   ├── openai_client.py    # OpenAI implementation
│   │   └── mock_client.py      # Mock for unit tests
│   ├── tools/
│   │   ├── base.py             # ToolRegistry + Tool ABC
│   │   ├── file_tools.py       # read_file, write_file, list_files
│   │   └── shell_tool.py       # run_shell, run_tests
│   ├── governance/             # DEEP DIMENSION
│   │   ├── guardrails.py       # GuardrailEngine
│   │   ├── sandbox.py          # Sandbox
│   │   ├── hitl.py             # HITLStateMachine
│   │   └── engine.py           # GovernanceEngine (composition)
│   ├── feedback/
│   │   └── engine.py           # FeedbackEngine
│   ├── memory/
│   │   └── store.py            # MemoryStore
│   ├── config/
│   │   └── loader.py           # ConfigLoader
│   └── credentials/
│       └── store.py            # CredentialStore
├── web/                        # WebUI layer
│   ├── app.py                  # FastAPI app
│   ├── routes.py               # REST + WebSocket routes
│   ├── session_manager.py      # Session manager
│   └── static/
│       ├── index.html          # Chat UI
│       ├── style.css
│       └── app.js
├── tests/                      # Unit + integration tests
│   ├── test_guardrails.py
│   ├── test_sandbox.py
│   ├── test_hitl.py
│   ├── test_governance_engine.py
│   ├── test_feedback.py
│   ├── test_credential_store.py
│   ├── test_config_loader.py
│   ├── test_loop_integration.py
│   └── test_mechanism_demo.py
├── demo/
│   └── mechanism_demo.py       # §A.6 mechanism demonstration script
├── harness_config.yaml         # Default config
├── pyproject.toml              # Package config + dependencies
├── Dockerfile                  # Container build
├── docker-compose.yml          # Local dev with volume
├── Makefile                    # make test, make run, make docker
├── .github/
│   └── workflows/
│       └── ci.yml              # CI with unit-test job
├── .gitignore
├── SPEC.md                     # This file
├── PLAN.md                     # Implementation plan (next step)
├── SPEC_PROCESS.md             # Brainstorming process doc
├── AGENT_LOG.md                # Agent work log
├── REFLECTION.md               # Reflection report
└── README.md                   # Project README
```
