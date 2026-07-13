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
