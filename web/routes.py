from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError
from web.session_manager import SessionManager
from pydantic import BaseModel
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class CredentialRequest(BaseModel):
    master_password: str
    api_key: str


class TaskRequest(BaseModel):
    task: str


class ApprovalRequest(BaseModel):
    request_id: str


def create_router(cred_store: CredentialStore) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index():
        static = Path(__file__).parent / "static" / "index.html"
        if static.exists():
            return FileResponse(str(static))
        return HTMLResponse("<h1>Coding Agent Harness</h1>")

    @router.get("/api/credentials")
    async def credential_status():
        return cred_store.status()

    @router.post("/api/credentials")
    async def store_credentials(req: CredentialRequest, request: Request):
        cred_store.store(req.api_key, req.master_password)
        sm: SessionManager = request.app.state.session_manager
        sm.set_master_password(req.master_password)
        return {"status": "stored"}

    @router.delete("/api/credentials")
    async def clear_credentials():
        cred_store.clear()
        return {"status": "cleared"}

    @router.post("/api/session")
    async def create_session(req: TaskRequest, request: Request):
        sm: SessionManager = request.app.state.session_manager
        session_id = await sm.create_session(req.task)
        asyncio.create_task(sm.run_session(session_id))
        return {"session_id": session_id}

    @router.get("/api/session/{session_id}")
    async def session_status(session_id: str, request: Request):
        sm: SessionManager = request.app.state.session_manager
        session = sm.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": session["id"],
            "task": session["task"],
            "status": session["status"],
            "events": session.get("events", []),
            "result": session.get("result"),
        }

    @router.post("/api/session/{session_id}/approve")
    async def approve_action(session_id: str, req: ApprovalRequest, request: Request):
        sm: SessionManager = request.app.state.session_manager
        session = sm.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        hitl = session.get("hitl")
        if hitl is None:
            raise HTTPException(status_code=400, detail="No pending approvals")
        from harness.governance.hitl import ApprovalState
        hitl.resolve(req.request_id, ApprovalState.APPROVED, "web_user")
        return {"status": "approved"}

    @router.post("/api/session/{session_id}/deny")
    async def deny_action(session_id: str, req: ApprovalRequest, request: Request):
        sm: SessionManager = request.app.state.session_manager
        session = sm.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        hitl = session.get("hitl")
        if hitl is None:
            raise HTTPException(status_code=400, detail="No pending approvals")
        from harness.governance.hitl import ApprovalState
        hitl.resolve(req.request_id, ApprovalState.DENIED, "web_user")
        return {"status": "denied"}

    @router.websocket("/ws/session/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        await websocket.accept()
        sm: SessionManager = websocket.app.state.session_manager
        session = sm.get_session(session_id)
        if session is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        session["websocket"] = websocket

        for event in session.get("events", []):
            await websocket.send_json(event)

        if session["status"] in ("completed", "failed"):
            result = session.get("result", {})
            await websocket.send_json({
                "type": "complete",
                "success": result.get("success", False),
                "iterations": result.get("iterations", 0),
                "reason": result.get("reason", ""),
            })
            await websocket.close()
            return

        try:
            while session["status"] in ("pending", "running"):
                await asyncio.sleep(0.5)
                pending = session.get("hitl")
                if pending:
                    for req in pending.get_pending_requests():
                        await websocket.send_json({
                            "type": "hitl_request",
                            "request_id": req.id,
                            "action": req.action.type,
                            "command": req.action.command,
                            "reason": req.reason,
                        })
            result = session.get("result", {})
            await websocket.send_json({
                "type": "complete",
                "success": result.get("success", False),
                "iterations": result.get("iterations", 0),
                "reason": result.get("reason", ""),
            })
        except WebSocketDisconnect:
            session["websocket"] = None
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            session["websocket"] = None

    return router
