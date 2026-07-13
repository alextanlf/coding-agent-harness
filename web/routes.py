from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError
from web.session_manager import SessionManager
from pydantic import BaseModel


class CredentialRequest(BaseModel):
    master_password: str
    api_key: str


class TaskRequest(BaseModel):
    task: str


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
    async def store_credentials(req: CredentialRequest):
        cred_store.store(req.api_key, req.master_password)
        return {"status": "stored"}

    @router.delete("/api/credentials")
    async def clear_credentials():
        cred_store.clear()
        return {"status": "cleared"}

    @router.post("/api/session")
    async def create_session(req: TaskRequest, request: Request):
        sm: SessionManager = request.app.state.session_manager
        session_id = await sm.create_session(req.task)
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
        }

    return router
