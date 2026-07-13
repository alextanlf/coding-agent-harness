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
            operation = "write" if action.type == "write_file" else "read"
            sandbox_decision = self.sandbox.check_path(action.path or "", operation)
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
