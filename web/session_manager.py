# web/session_manager.py
import asyncio
import logging
import os
import secrets
from uuid import uuid4
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError
from harness.core.loop import run_loop, EventEmitter
from harness.llm.openai_client import OpenAIClient
from harness.tools.base import ToolRegistry
from harness.tools.file_tools import WriteFileTool, ReadFileTool, ListFilesTool
from harness.tools.shell_tool import RunShellTool
from harness.governance.engine import GovernanceEngine
from harness.governance.guardrails import GuardrailEngine
from harness.governance.sandbox import Sandbox
from harness.governance.hitl import HITLStateMachine, ApprovalState
from harness.feedback.engine import FeedbackEngine
from harness.memory.store import MemoryStore
from harness.config.loader import ConfigLoader
from harness.core.models import GuardrailRule

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, workspace_root: Path, credential_path: Path):
        self._workspace_root = Path(workspace_root)
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._cred_store = CredentialStore(store_path=credential_path)
        self._sessions: dict[str, dict] = {}

        # Auto-generate and persist a server-side secret for encrypting API keys.
        # This frees the user from managing a master password — the server
        # handles encryption/decryption transparently. The secret survives
        # restarts because it's stored on the persistent disk.
        self._secret_path = self._workspace_root.parent / "server_secret"
        self._server_secret = self._load_or_create_secret()

    def _load_or_create_secret(self) -> str:
        """Load the server-side secret from disk, or generate a new one."""
        try:
            if self._secret_path.exists():
                return self._secret_path.read_text().strip()
        except Exception:
            pass
        secret = secrets.token_urlsafe(32)
        try:
            self._secret_path.parent.mkdir(parents=True, exist_ok=True)
            self._secret_path.write_text(secret)
            logger.info("Generated new server-side secret for credential encryption")
        except Exception as e:
            logger.warning(f"Could not persist server secret: {e}")
        return secret

    async def create_session(self, task: str, websocket=None) -> str:
        session_id = str(uuid4())
        session_ws = self._workspace_root / session_id
        session_ws.mkdir(parents=True, exist_ok=True)

        self._sessions[session_id] = {
            "id": session_id,
            "task": task,
            "status": "pending",
            "workspace": session_ws,
            "events": [],
            "hitl": None,
            "websocket": websocket,
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
        hitl = HITLStateMachine(timeout_seconds=300)
        session["hitl"] = hitl
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
        memory = MemoryStore(system_prompt=(
            "You are a coding agent. You can read files, write files, list files, "
            "run shell commands, and run tests. You respond with JSON actions.\n"
            "Action format: {\"type\": \"read_file\", \"path\": \"...\"}\n"
            "Types: read_file, write_file, list_files, run_shell, run_tests, task_complete\n"
            "For write_file: {\"type\": \"write_file\", \"path\": \"...\", \"content\": \"...\"}\n"
            "For run_shell: {\"type\": \"run_shell\", \"command\": \"...\"}\n"
            "When done: {\"type\": \"task_complete\"}"
        ))

        llm = self._create_llm(config)
        if llm is None:
            session["status"] = "failed"
            session["result"] = {"success": False, "iterations": 0, "reason": "No API key configured"}
            await self._emit(session_id, "error", {"message": "No API key configured. Click Settings to add your OpenAI key."})
            return

        ws = session.get("websocket")

        class WebSocketEmitter(EventEmitter):
            async def emit(self_inner, event_type: str, data: dict):
                session["events"].append({"type": event_type, "data": data})
                if ws is not None:
                    try:
                        await ws.send_json({"type": event_type, **data})
                    except Exception:
                        pass

        emitter = WebSocketEmitter()

        try:
            result = await run_loop(
                task=session["task"],
                llm=llm,
                tools=reg,
                governance=governance,
                feedback=feedback,
                memory=memory,
                config=config,
                emitter=emitter,
            )
            session["status"] = "completed" if result.success else "failed"
            session["result"] = {
                "success": result.success,
                "iterations": result.iterations,
                "reason": result.reason,
            }
        except Exception as e:
            logger.error(f"Session {session_id} failed: {e}")
            session["status"] = "failed"
            session["result"] = {"success": False, "iterations": 0, "reason": str(e)}
            await emitter.emit("error", {"message": str(e)})

    def _create_llm(self, config):
        # Try credential store with server-side secret (survives restarts)
        try:
            status = self._cred_store.status()
            if status.get("configured"):
                try:
                    api_key = self._cred_store.load(self._server_secret)
                    logger.info("Loaded API key from credential store (server-side secret)")
                    return OpenAIClient(api_key=api_key, model=config.model)
                except CredentialError as e:
                    logger.warning(f"Credential store load failed: {e}")
        except Exception as e:
            logger.warning(f"Credential store check failed: {e}")

        # Fallback: OPENAI_API_KEY environment variable
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            logger.info("Using OPENAI_API_KEY from environment variable")
            return OpenAIClient(api_key=env_key, model=config.model)

        logger.warning("No API key available")
        return None

    def store_api_key(self, api_key: str):
        """Store API key encrypted with the server-side secret. No master password needed."""
        self._cred_store.store(api_key, self._server_secret)
        logger.info("API key stored with server-side secret")

    def clear_api_key(self):
        """Clear stored API key."""
        self._cred_store.clear()
        logger.info("API key cleared")

    async def _emit(self, session_id: str, event_type: str, data: dict):
        session = self._sessions.get(session_id)
        if session is None:
            return
        session["events"].append({"type": event_type, "data": data})
        ws = session.get("websocket")
        if ws is not None:
            try:
                await ws.send_json({"type": event_type, **data})
            except Exception:
                pass

    def _rule_from_pattern(self, pattern: str, severity: str):
        return GuardrailRule(pattern=pattern, severity=severity, description=f"Config rule: {pattern}")
