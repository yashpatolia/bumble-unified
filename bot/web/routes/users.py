import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import manager
from web.auth import is_guest, require_admin, require_auth

router = APIRouter(prefix="/api/users", tags=["users"])
_OWNER_ID = int(os.getenv("PANEL_ADMIN_DISCORD_ID", "0"))


class CreateUser(BaseModel):
    discord_id: str
    discord_name: str
    is_admin: bool = False
    can_control_bots: bool = False
    can_fetch_api: bool = False
    can_manage_links: bool = False
    can_manage_members: bool = False
    can_manage_config: bool = False


class UpdateUser(BaseModel):
    is_admin: bool | None = None
    can_control_bots: bool = False
    can_fetch_api: bool = False
    can_manage_links: bool = False
    can_manage_members: bool = False
    can_manage_config: bool = False


def _is_owner(claims: dict) -> bool:
    return bool(claims.get("owner"))


def _require_can_manage(target: tuple, claims: dict) -> None:
    """Hierarchy: owner > admin > everyone else. Only the owner may touch an admin or the owner."""
    if _is_owner(claims):
        return
    if bool(target[2]) or int(target[0]) == _OWNER_ID:
        raise HTTPException(status_code=403, detail="Only the owner can change an admin or the owner")


def _row_to_dict(row: tuple) -> dict:
    return {
        "discord_id": str(row[0]),
        "discord_name": row[1],
        "is_admin": bool(row[2]),
        "can_control_bots": bool(row[3]),
        "can_fetch_api": bool(row[4]) if len(row) > 4 else False,
        "can_manage_links": bool(row[5]) if len(row) > 5 else False,
        "can_manage_members": bool(row[6]) if len(row) > 6 else False,
        "can_manage_config": bool(row[7]) if len(row) > 7 else False,
        "is_owner": int(row[0]) == _OWNER_ID,
    }


@router.get("")
def list_users(claims=Depends(require_auth)):
    # Read-only for everyone signed in; only admins can change anything (see the routes below).
    users = [_row_to_dict(r) for r in manager.get_all_panel_users()]
    if is_guest(claims):
        users = [{**u, "discord_id": "hidden"} for u in users]
    return users


@router.post("", status_code=201)
def create_user(body: CreateUser, claims=Depends(require_admin)):
    if body.is_admin and not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Only the owner can grant admin")
    discord_id = int(body.discord_id)
    if manager.get_panel_user(discord_id):
        raise HTTPException(status_code=409, detail="User already exists")
    manager.create_panel_user(discord_id, body.discord_name, body.is_admin, body.can_control_bots, body.can_fetch_api, body.can_manage_links, body.can_manage_members, body.can_manage_config)
    return {"status": "created"}


@router.patch("/{discord_id}")
def update_user(discord_id: int, body: UpdateUser, request: Request, claims=Depends(require_admin)):
    existing = manager.get_panel_user(discord_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    _require_can_manage(existing, claims)
    final_is_admin = body.is_admin if body.is_admin is not None else bool(existing[2])
    if final_is_admin != bool(existing[2]) and not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Only the owner can grant or revoke admin")
    if int(claims["sub"]) == discord_id and not final_is_admin:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin access")
    manager.update_panel_user_permissions(discord_id, final_is_admin, body.can_control_bots, body.can_fetch_api, body.can_manage_links, body.can_manage_members, body.can_manage_config)
    return {"status": "updated"}


@router.delete("/{discord_id}")
def delete_user(discord_id: int, request: Request, claims=Depends(require_admin)):
    if int(claims["sub"]) == discord_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    existing = manager.get_panel_user(discord_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    _require_can_manage(existing, claims)
    manager.delete_panel_user(discord_id)
    return {"status": "deleted"}
