"""In-game guild actions triggered from the panel: kick a member, invite a player.
The panel process never touches Minecraft; it forwards to the bot process's IPC API,
which validates the input and sends the /guild command."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import GUILD_CONFIGS
from db import manager
from web.auth import require_manage_members
from web.ipc_client import ipc_post_json

router = APIRouter(prefix="/api/bots", tags=["member-actions"])


class KickBody(BaseModel):
    reason: str = ""


class ExcuseBody(BaseModel):
    reason: str = ""
    until: str | None = None  # YYYY-MM-DD, or None for "until removed"


class InviteBody(BaseModel):
    ign: str


def _check_key(key: str) -> None:
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")


@router.post("/{key}/members/{ign}/kick")
async def kick_member(key: str, ign: str, body: KickBody, claims=Depends(require_manage_members)):
    _check_key(key)
    return await ipc_post_json(f"/guild/{key}/kick", {"ign": ign, "reason": body.reason, "actor": claims.get("name", "unknown")})


def _roster_ign(key: str, ign: str) -> str:
    """The roster's own spelling of this IGN, or a 404 so typos never create rows."""
    for row in manager.get_guild_members(key):
        if row[0].lower() == ign.lower():
            return row[0]
    raise HTTPException(status_code=404, detail=f"{ign} is not in this guild's roster")


@router.post("/{key}/members/{ign}/excuse")
async def excuse_member(key: str, ign: str, body: ExcuseBody, claims=Depends(require_manage_members)):
    _check_key(key)
    canonical = _roster_ign(key, ign)
    until = None
    if body.until:
        try:
            until = datetime.date.fromisoformat(body.until)
        except ValueError:
            raise HTTPException(status_code=400, detail="The end date must look like 2026-11-03")
        today = datetime.date.today()
        if until < today:
            raise HTTPException(status_code=400, detail="The end date cannot be in the past")
        if until > today + datetime.timedelta(days=366):
            raise HTTPException(status_code=400, detail="Excuses can last at most a year")
    reason = " ".join(body.reason.split())[:200] or None
    manager.set_excused(key, canonical, reason, until, claims.get("name", "unknown"))
    return {"status": "excused", "ign": canonical, "reason": reason, "until": until.isoformat() if until else None}


@router.delete("/{key}/members/{ign}/excuse")
async def remove_excuse(key: str, ign: str, claims=Depends(require_manage_members)):
    _check_key(key)
    manager.remove_excused(key, _roster_ign(key, ign))
    return {"status": "removed", "ign": ign}


@router.post("/{key}/invite")
async def invite_player(key: str, body: InviteBody, claims=Depends(require_manage_members)):
    _check_key(key)
    return await ipc_post_json(f"/guild/{key}/invite", {"ign": body.ign, "actor": claims.get("name", "unknown")})
