"""Read-only guild data: live overview/members (proxied to the bot process's
IPC API) and the message-count leaderboard (DB-only, no IPC involved)."""
import datetime

from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from db import manager
from web.auth import require_auth
from web.ipc_client import ipc_get, ipc_get_or_raise, LONG_TIMEOUT

router = APIRouter(prefix="/api/bots", tags=["bots"])


@router.get("/{key}/overview")
async def get_guild_overview(key: str, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    overview = await ipc_get(f"/guild/{key}/overview")
    if overview is not None:
        return overview
    config = GUILD_CONFIGS[key]
    return {
        "key": key,
        "name": config.display_name,
        "short_name": config.short_name,
        "username": config.mc_username,
        "connected": False,
        "member_count": 0,
        "recent_chat": [],
        "recent_events": [],
    }


@router.get("/{key}/members")
async def get_guild_members(key: str, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    return await ipc_get_or_raise(f"/guild/{key}/members", timeout=LONG_TIMEOUT)


@router.get("/{key}/leaderboard")
async def get_leaderboard(key: str, period: str = "lifetime", _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    now = datetime.datetime.utcnow()
    if period == "month":
        period_key = now.strftime('%Y-%m')
    elif period == "week":
        period_key = now.strftime('%G-W%V')
    else:
        period = "lifetime"
        period_key = ""
    rows = manager.get_message_leaderboard(key, period, period_key)
    return {"leaderboard": [
        {"ign": r[0], "count": r[1], "uuid": r[2] or None, "discord_name": r[3] or None, "discord_id": str(r[4]) if r[4] else None, "discord_avatar": r[5] or None}
        for r in rows
    ]}
