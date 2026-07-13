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
