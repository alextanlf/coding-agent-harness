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
