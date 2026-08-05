from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from web.auth import (
    complete_login,
    discord_oauth_url,
    exchange_code,
    require_auth,
)
from web.routes import api_usage, bot_control, dyes, guild_data, links, stats_refresh, users

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Bumble", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(bot_control.router)
    app.include_router(guild_data.router)
    app.include_router(links.router)
    app.include_router(stats_refresh.router)
    app.include_router(api_usage.router)
    app.include_router(users.router)
    app.include_router(dyes.router)

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

        token = complete_login(user)
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
