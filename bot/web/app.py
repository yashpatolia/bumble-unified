import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from db import manager
from web.auth import (
    create_token,
    discord_oauth_url,
    exchange_code,
    require_auth,
    verify_token,
)
from web.logs import broadcaster
from web.routes import bots, users

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
_ADMIN_ID = int(os.getenv("PANEL_ADMIN_DISCORD_ID", "0"))


def create_app() -> FastAPI:
    app = FastAPI(title="Bumble", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(bots.router)
    app.include_router(users.router)

    # --- Auth ---

    @app.get("/auth/discord")
    def discord_login():
        return RedirectResponse(discord_oauth_url())

    @app.get("/auth/callback")
    async def discord_callback(code: str = None, error: str = None):
        if error or not code:
            return RedirectResponse("/?error=oauth_denied")
        try:
            user = await exchange_code(code)
        except HTTPException:
            return RedirectResponse("/?error=oauth_failed")

        discord_id = int(user["id"])
        discord_name = user.get("username", "Unknown")
        avatar_hash = user.get("avatar")
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png?size=64"
        else:
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{(discord_id >> 22) % 6}.png"

        if discord_id == _ADMIN_ID and not manager.get_panel_user(discord_id):
            manager.create_panel_user(discord_id, discord_name, is_admin=True)

        panel_user = manager.get_panel_user(discord_id)
        if panel_user:
            manager.upsert_panel_user_name(discord_id, discord_name)
            manager.update_user_avatar(discord_id, avatar_url)

        is_admin = bool(panel_user[2]) if panel_user else False
        can_control_bots = bool(panel_user[3]) if panel_user else False
        can_fetch_api = bool(panel_user[4]) if panel_user and len(panel_user) > 4 else False
        can_manage_links = bool(panel_user[5]) if panel_user and len(panel_user) > 5 else False
        token = create_token(discord_id, discord_name, is_admin, can_control_bots, avatar_url,
                             is_owner=(discord_id == _ADMIN_ID), can_fetch_api=can_fetch_api,
                             can_manage_links=can_manage_links)
        return RedirectResponse(f"/?token={token}")

    # --- Current user ---

    @app.get("/api/me")
    def me(request: Request):
        claims = require_auth(request)
        return {
            "discord_id": claims["sub"],
            "discord_name": claims["name"],
            "is_admin": claims["admin"],
            "can_control_bots": claims.get("bots", False),
            "can_fetch_api": claims.get("fetch_api", False),
            "can_manage_links": claims.get("manage_links", False),
            "avatar_url": claims.get("avatar", ""),
            "is_owner": claims.get("owner", False),
        }

    # --- Live log stream ---

    @app.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket):
        token = websocket.query_params.get("token")
        if not token:
            return
        try:
            claims = verify_token(token)
        except HTTPException:
            return
        if not claims.get("logs") and not claims.get("admin"):
            return

        await websocket.accept()

        # Send current history immediately
        history = broadcaster.snapshot()
        for record in history:
            try:
                await websocket.send_text(json.dumps(record))
            except Exception:
                return
        sent = len(history)

        # Poll for new records every 200 ms
        try:
            while True:
                await asyncio.sleep(0.2)
                new = broadcaster.get_after(sent)
                for record in new:
                    await websocket.send_text(json.dumps(record))
                sent += len(new)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    # --- Serve built frontend (SPA fallback) ---

    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        _index_html = (FRONTEND_DIST / "index.html").read_text(encoding="utf-8")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            return HTMLResponse(_index_html)
    else:
        @app.get("/{full_path:path}", include_in_schema=False)
        async def no_frontend(full_path: str):
            return JSONResponse(
                {"error": "Frontend not built. Run: cd frontend && npm run build"},
                status_code=503,
            )

    return app
