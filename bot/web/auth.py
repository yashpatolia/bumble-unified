import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import aiohttp
import jwt
from fastapi import HTTPException, Request

from config import PANEL_ADMIN_DISCORD_ID
from db import manager

DISCORD_API = "https://discord.com/api/v10"
_CLIENT_ID = os.getenv("PANEL_DISCORD_CLIENT_ID")
_CLIENT_SECRET = os.getenv("PANEL_DISCORD_CLIENT_SECRET")
_REDIRECT_URI = os.getenv("PANEL_REDIRECT_URI")
_JWT_SECRET = os.getenv("PANEL_JWT_SECRET")
_JWT_ALGO = "HS256"
_JWT_EXPIRE_HOURS = 24 * 30  # 30 days


def discord_oauth_url() -> str:
    params = {
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


def create_token(discord_id: int, discord_name: str, is_admin: bool, can_control_bots: bool,
                 avatar_url: str = "", is_owner: bool = False, can_fetch_api: bool = False,
                 can_manage_links: bool = False) -> str:
    payload = {
        "sub": str(discord_id),
        "name": discord_name,
        "admin": is_admin,
        "bots": can_control_bots,
        "fetch_api": can_fetch_api,
        "manage_links": can_manage_links,
        "avatar": avatar_url,
        "owner": is_owner,
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


def require_bot_control(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("bots") and not claims.get("admin"):
        raise HTTPException(status_code=403, detail="Bot control access not permitted")
    return claims


def require_api_fetch(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("fetch_api") and not claims.get("admin"):
        raise HTTPException(status_code=403, detail="API fetch access not permitted")
    return claims


def require_manage_links(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("manage_links") and not claims.get("admin"):
        raise HTTPException(status_code=403, detail="Manage links access not permitted")
    return claims


def require_owner(request: Request) -> dict:
    claims = require_auth(request)
    if not claims.get("owner"):
        raise HTTPException(status_code=403, detail="Owner access required")
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


def complete_login(discord_user: dict) -> str:
    """Given a Discord user profile from exchange_code(), auto-provision the
    panel owner on first login, refresh their stored name/avatar, and issue
    a JWT. Returns the token."""
    discord_id = int(discord_user["id"])
    discord_name = discord_user.get("username", "Unknown")
    avatar_hash = discord_user.get("avatar")
    if avatar_hash:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png?size=64"
    else:
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{(discord_id >> 22) % 6}.png"

    if discord_id == PANEL_ADMIN_DISCORD_ID and not manager.get_panel_user(discord_id):
        manager.create_panel_user(discord_id, discord_name, is_admin=True)

    panel_user = manager.get_panel_user(discord_id)
    if panel_user:
        manager.upsert_panel_user_name(discord_id, discord_name)
        manager.update_user_avatar(discord_id, avatar_url)

    is_admin = bool(panel_user[2]) if panel_user else False
    can_control_bots = bool(panel_user[3]) if panel_user else False
    can_fetch_api = bool(panel_user[4]) if panel_user and len(panel_user) > 4 else False
    can_manage_links = bool(panel_user[5]) if panel_user and len(panel_user) > 5 else False
    return create_token(discord_id, discord_name, is_admin, can_control_bots, avatar_url,
                         is_owner=(discord_id == PANEL_ADMIN_DISCORD_ID), can_fetch_api=can_fetch_api,
                         can_manage_links=can_manage_links)
