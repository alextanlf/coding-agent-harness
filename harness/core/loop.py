# harness/core/loop.py
import logging
from dataclasses import dataclass
from harness.core.models import Message, Action, RunResult, ShellResult
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

    had_block = False

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
            if had_block:
                await emitter.emit("complete", {"success": False, "iterations": iteration + 1})
                return RunResult(success=False, iterations=iteration + 1, reason="blocked_action")
            await emitter.emit("complete", {"success": True, "iterations": iteration + 1})
            return RunResult(success=True, iterations=iteration + 1, reason="task_complete")

        decision = await governance.evaluate(action)
        if decision.blocked:
            had_block = True
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="system", content=f"Action blocked: {decision.reason}"))
            await emitter.emit("blocked", {"reason": decision.reason})
            continue

        if action.type == "run_tests":
            test_action = Action(type="run_shell", command=config.feedback.test_command)
            try:
                result = await tools.dispatch(test_action)
            except ValueError as e:
                memory._history.append(Message(role="assistant", content=response))
                memory._history.append(Message(role="system", content=f"Tool error: {e}"))
                continue
            shell_result = ShellResult(
                stdout=result.output, stderr=result.error, exit_code=result.exit_code
            )
            test_feedback = feedback.parse_test_output(shell_result)
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="user", content=feedback.inject(test_feedback).content))
            await emitter.emit("test_result", {
                "passed": test_feedback.passed,
                "failures": [{"name": f.name, "message": f.message} for f in test_feedback.failures],
            })
            continue

        try:
            result = await tools.dispatch(action)
        except ValueError as e:
            memory._history.append(Message(role="assistant", content=response))
            memory._history.append(Message(role="system", content=f"Tool error: {e}"))
            continue

        memory.record(action, ShellResult(
            stdout=result.output, stderr=result.error, exit_code=result.exit_code
        ))

    await emitter.emit("complete", {"success": False, "iterations": config.max_iterations})
    return RunResult(success=False, iterations=config.max_iterations, reason="max_iterations")
