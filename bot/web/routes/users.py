import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import manager
from web.auth import require_admin

router = APIRouter(prefix="/api/users", tags=["users"])
_OWNER_ID = int(os.getenv("PANEL_ADMIN_DISCORD_ID", "0"))


class CreateUser(BaseModel):
    discord_id: str
    discord_name: str
    is_admin: bool = False
    can_view_logs: bool = True
    can_control_bots: bool = False
    can_fetch_api: bool = False


class UpdateUser(BaseModel):
    is_admin: bool | None = None
    can_view_logs: bool
    can_control_bots: bool = False
    can_fetch_api: bool = False


def _row_to_dict(row: tuple) -> dict:
    return {
        "discord_id": str(row[0]),
        "discord_name": row[1],
        "is_admin": bool(row[2]),
        "can_view_logs": bool(row[3]),
        "can_control_bots": bool(row[4]),
        "can_fetch_api": bool(row[5]) if len(row) > 5 else False,
        "is_owner": int(row[0]) == _OWNER_ID,
    }


@router.get("")
def list_users(_=Depends(require_admin)):
    return [_row_to_dict(r) for r in manager.get_all_panel_users()]


@router.post("", status_code=201)
def create_user(body: CreateUser, _=Depends(require_admin)):
    discord_id = int(body.discord_id)
    if manager.get_panel_user(discord_id):
        raise HTTPException(status_code=409, detail="User already exists")
    manager.create_panel_user(discord_id, body.discord_name, body.is_admin, body.can_view_logs, body.can_control_bots, body.can_fetch_api)
    return {"status": "created"}


@router.patch("/{discord_id}")
def update_user(discord_id: int, body: UpdateUser, request: Request, claims=Depends(require_admin)):
    existing = manager.get_panel_user(discord_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    final_is_admin = body.is_admin if body.is_admin is not None else bool(existing[2])
    if int(claims["sub"]) == discord_id and not final_is_admin:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin access")
    manager.update_panel_user_permissions(discord_id, final_is_admin, body.can_view_logs, body.can_control_bots, body.can_fetch_api)
    return {"status": "updated"}


@router.delete("/{discord_id}")
def delete_user(discord_id: int, request: Request, claims=Depends(require_admin)):
    if int(claims["sub"]) == discord_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if not manager.get_panel_user(discord_id):
        raise HTTPException(status_code=404, detail="User not found")
    manager.delete_panel_user(discord_id)
    return {"status": "deleted"}
