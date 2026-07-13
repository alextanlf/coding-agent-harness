import asyncio
from datetime import datetime
from uuid import uuid4
from enum import StrEnum
from harness.core.models import Action, ApprovalRequest


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class HITLStateMachine:
    """Manages approval requests with async pause/resume via asyncio.Event."""

    def __init__(self, timeout_seconds: int = 120):
        self._timeout = timeout_seconds
        self._pending: dict[str, ApprovalRequest] = {}
        self._events: dict[str, asyncio.Event] = {}

    async def request_approval(self, action: Action, reason: str) -> ApprovalRequest:
        request_id = str(uuid4())
        request = ApprovalRequest(
            id=request_id,
            action=action,
            reason=reason,
            state=ApprovalState.PENDING,
            created_at=datetime.now(),
        )
        self._pending[request_id] = request
        self._events[request_id] = asyncio.Event()

        try:
            await asyncio.wait_for(self._events[request_id].wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            request.state = ApprovalState.TIMEOUT
            request.decided_at = datetime.now()
        finally:
            self._cleanup(request_id)

        return request

    def resolve(self, request_id: str, decision: ApprovalState, user: str):
        if request_id not in self._pending:
            raise KeyError(f"No pending request with id {request_id}")
        request = self._pending[request_id]
        if request.state != ApprovalState.PENDING:
            raise KeyError(f"Request {request_id} already resolved: {request.state}")
        request.state = decision
        request.decided_at = datetime.now()
        request.decided_by = user
        self._events[request_id].set()

    def get_pending_requests(self) -> list[ApprovalRequest]:
        return [r for r in self._pending.values() if r.state == ApprovalState.PENDING]

    def _cleanup(self, request_id: str):
        if request_id in self._events:
            del self._events[request_id]
