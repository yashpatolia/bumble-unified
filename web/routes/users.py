from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import manager
from web.auth import require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUser(BaseModel):
    discord_id: int
    discord_name: str
    is_admin: bool = False
    can_view_logs: bool = True


class UpdateUser(BaseModel):
    is_admin: bool
    can_view_logs: bool


def _row_to_dict(row: tuple) -> dict:
    return {
        "discord_id": row[0],
        "discord_name": row[1],
        "is_admin": bool(row[2]),
        "can_view_logs": bool(row[3]),
    }


@router.get("")
def list_users(_=Depends(require_admin)):
    return [_row_to_dict(r) for r in manager.get_all_panel_users()]


@router.post("", status_code=201)
def create_user(body: CreateUser, _=Depends(require_admin)):
    if manager.get_panel_user(body.discord_id):
        raise HTTPException(status_code=409, detail="User already exists")
    manager.create_panel_user(body.discord_id, body.discord_name, body.is_admin, body.can_view_logs)
    return {"status": "created"}


@router.patch("/{discord_id}")
def update_user(discord_id: int, body: UpdateUser, request: Request, claims=Depends(require_admin)):
    if int(claims["sub"]) == discord_id and not body.is_admin:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin access")
    if not manager.get_panel_user(discord_id):
        raise HTTPException(status_code=404, detail="User not found")
    manager.update_panel_user_permissions(discord_id, body.is_admin, body.can_view_logs)
    return {"status": "updated"}


@router.delete("/{discord_id}")
def delete_user(discord_id: int, request: Request, claims=Depends(require_admin)):
    if int(claims["sub"]) == discord_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if not manager.get_panel_user(discord_id):
        raise HTTPException(status_code=404, detail="User not found")
    manager.delete_panel_user(discord_id)
    return {"status": "deleted"}
