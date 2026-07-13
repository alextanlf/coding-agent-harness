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
        self._workspace_root = Path(workspace_root)
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
