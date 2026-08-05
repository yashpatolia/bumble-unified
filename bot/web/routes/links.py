"""Link/unlink a guild_members row's UUID to a Discord account directly from
the panel — DB-only, no bot-process IPC involved."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import GUILD_CONFIGS
from db import manager
from web.auth import require_manage_links

router = APIRouter(prefix="/api/bots", tags=["bots"])


class LinkMemberBody(BaseModel):
    discord_id: str
    discord_name: str


@router.post("/{key}/members/{ign}/link")
async def link_member(key: str, ign: str, body: LinkMemberBody, _=Depends(require_manage_links)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    uuid = manager.get_member_uuid(key, ign)
    if not uuid:
        raise HTTPException(status_code=400, detail="Member has no UUID — refresh stats first")
    try:
        discord_id = int(body.discord_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Discord ID")
    manager.link_user(uuid, ign, discord_id, body.discord_name)
    return {"status": "linked"}


@router.delete("/{key}/members/{ign}/link")
async def unlink_member(key: str, ign: str, _=Depends(require_manage_links)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    uuid = manager.get_member_uuid(key, ign)
    if not uuid:
        raise HTTPException(status_code=400, detail="Member has no UUID")
    manager.unlink_user(uuid)
    return {"status": "unlinked"}
