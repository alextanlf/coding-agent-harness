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
