from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from web.routes import create_router
from web.session_manager import SessionManager
from harness.credentials.store import CredentialStore


def create_app(workspace_root: str = ".agent/workspace",
               credential_path: str = ".agent/credentials.enc") -> FastAPI:
    app = FastAPI(title="Coding Agent Harness")

    ws_root = Path(workspace_root)
    ws_root.mkdir(parents=True, exist_ok=True)

    cred_store = CredentialStore(store_path=Path(credential_path))
    app.state.credential_store = cred_store
    app.state.workspace_root = ws_root
    app.state.session_manager = SessionManager(
        workspace_root=ws_root,
        credential_path=Path(credential_path),
    )

    app.include_router(create_router(cred_store))

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()
