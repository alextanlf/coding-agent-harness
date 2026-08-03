# web/session_manager.py
import asyncio
import logging
from uuid import uuid4
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError
from harness.core.loop import run_loop, EventEmitter
from harness.llm.openai_client import OpenAIClient
from harness.llm.mock_client import MockLLMClient
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
            await self._emit(session_id, "error", {"message": "No API key configured. Go to Settings to add your OpenAI key."})
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
        try:
            status = self._cred_store.status()
            if not status.get("configured"):
                return None
        except Exception:
            return None

        master_password = getattr(self, '_master_password', None)
        if master_password is None:
            return None

        try:
            api_key = self._cred_store.load(master_password)
            return OpenAIClient(api_key=api_key, model=config.model)
        except CredentialError as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def set_master_password(self, password: str):
        self._master_password = password

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
