import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import aiohttp
import jwt
from fastapi import HTTPException, Request

DISCORD_API = "https://discord.com/api/v10"
_CLIENT_ID = os.getenv("PANEL_DISCORD_CLIENT_ID")
_CLIENT_SECRET = os.getenv("PANEL_DISCORD_CLIENT_SECRET")
_REDIRECT_URI = os.getenv("PANEL_REDIRECT_URI")
_JWT_SECRET = os.getenv("PANEL_JWT_SECRET")
_JWT_ALGO = "HS256"
_JWT_EXPIRE_HOURS = 24


def discord_oauth_url() -> str:
    params = {
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


def create_token(discord_id: int, discord_name: str, is_admin: bool, can_view_logs: bool, can_control_bots: bool, avatar_url: str = "") -> str:
    payload = {
        "sub": str(discord_id),
        "name": discord_name,
        "admin": is_admin,
        "logs": can_view_logs,
        "bots": can_control_bots,
        "avatar": avatar_url,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _extract_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    return auth[7:]


def require_auth(request: Request) -> dict:
    return verify_token(_extract_token(request))


def require_admin(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims


def require_logs(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("logs") and not claims.get("admin"):
        raise HTTPException(status_code=403, detail="Log access not permitted")
    return claims


def require_bot_control(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("bots") and not claims.get("admin"):
        raise HTTPException(status_code=403, detail="Bot control access not permitted")
    return claims


async def exchange_code(code: str) -> dict:
    """Exchange a Discord OAuth2 authorization code for the user's Discord profile."""
    async with aiohttp.ClientSession() as session:
        token_payload = {
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _REDIRECT_URI,
        }
        async with session.post(f"{DISCORD_API}/oauth2/token", data=token_payload) as resp:
            token_data = await resp.json()

        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Discord token exchange failed")

        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        async with session.get(f"{DISCORD_API}/users/@me", headers=headers) as resp:
            return await resp.json()
