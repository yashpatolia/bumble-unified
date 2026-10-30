import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import manager
from web.auth import is_guest, require_auth, require_manage_config

router = APIRouter(prefix="/api/dyes", tags=["dyes"])


def _build_profile(uuid: str, ign: str, discord_name, discord_avatar) -> dict:
    unlocked = set(manager.get_unlocked_dyes(uuid))
    dyes = [
        {
            "dye_id": dye_id,
            "dye_name": dye_name,
            "hex": hex_color,
            "weight": weight,
            "odds": f"1 in {round(100 / weight):,}",
            "unlocked": dye_id in unlocked,
        }
        for dye_id, dye_name, weight, hex_color in manager.get_all_dyes()
    ]
    return {
        "linked": True,
        "uuid": uuid,
        "ign": ign,
        "discord_name": discord_name,
        "discord_avatar": discord_avatar,
        "dyes": dyes,
    }


@router.get("/me")
async def get_my_dyes(claims=Depends(require_auth)):
    if is_guest(claims):
        return {"linked": False}
    row = manager.get_user_by_discord(int(claims["sub"]))
    if row is None:
        return {"linked": False}
    ign, discord_name, uuid = row
    return _build_profile(uuid, ign, discord_name or claims.get("name"), claims.get("avatar"))


@router.get("/search")
async def search_dyes(q: str = "", claims=Depends(require_auth)):
    q = q.strip()
    if not q:
        return {"results": []}
    rows = manager.search_users_with_dye_counts(q, limit=20)
    return {
        "results": [
            {
                "uuid": r[0],
                "ign": r[1],
                "discord_id": None if is_guest(claims) else (str(r[2]) if r[2] else None),
                "discord_name": r[3],
                "discord_avatar": r[4],
                "unlocked_count": r[5],
            }
            for r in rows
        ]
    }


@router.get("/user/{uuid}")
async def get_user_dyes(uuid: str, _=Depends(require_auth)):
    row = manager.get_user_by_uuid(uuid)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown player")
    ign, discord_id, discord_name, discord_avatar = row
    return _build_profile(uuid, ign, discord_name, discord_avatar)


@router.get("/recent")
async def get_recent_drops(_=Depends(require_auth)):
    rows = manager.get_recent_drops(limit=20)
    return {
        "drops": [
            {
                "dye_id": r[0],
                "dye_name": r[1],
                "hex": r[2],
                "unlocked_at": r[3].isoformat() if r[3] else None,
                "uuid": r[4],
                "ign": r[5],
                "discord_name": r[6],
                "discord_avatar": r[7],
            }
            for r in rows
        ]
    }


# --- Dye catalog editing (Config page). Weights are each dye's percent chance per guild chat
# message (utils/roll_dye.py rolls 0-100); whatever the weights don't cover is "no drop".

_DYE_ID_RE = re.compile(r"^[a-z0-9_]{2,40}$")
_HEX_RE = re.compile(r"^[0-9A-Fa-f]{6}$")


class DyeBody(BaseModel):
    dye_name: str
    weight: float
    hex: str
    role_id: Optional[str] = None
    emoji_id: Optional[str] = None


def _discord_id(value: Optional[str], what: str) -> Optional[int]:
    value = (value or "").strip()
    if not value:
        return None
    if not re.fullmatch(r"\d{17,20}", value):
        raise HTTPException(status_code=400, detail=f"{what} must be a Discord ID (17-20 digits)")
    return int(value)


def _catalog() -> dict:
    dyes = manager.get_dye_catalog()
    for d in dyes:
        d["role_id"] = str(d["role_id"]) if d["role_id"] else None
        d["emoji_id"] = str(d["emoji_id"]) if d["emoji_id"] else None
        d["odds"] = f"1 in {round(100 / d['weight']):,}" if d["weight"] else "never"
    return {"dyes": dyes, "total_weight": sum(d["weight"] for d in dyes)}


@router.get("/catalog")
async def get_catalog(_=Depends(require_auth)):
    return _catalog()


@router.put("/catalog/{dye_id}")
async def save_dye(dye_id: str, body: DyeBody, _=Depends(require_manage_config)):
    """Adds a dye, or updates it if the id already exists."""
    if not _DYE_ID_RE.match(dye_id):
        raise HTTPException(status_code=400, detail="Dye ID must be 2-40 lowercase letters, digits or underscores, e.g. mango_dye")
    name = body.dye_name.strip()
    if not 1 <= len(name) <= 40:
        raise HTTPException(status_code=400, detail="Name must be 1-40 characters")
    if not 0 < body.weight <= 100:
        raise HTTPException(status_code=400, detail="Weight must be above 0 and at most 100 (percent chance per message)")
    if not _HEX_RE.match(body.hex.strip().lstrip("#")):
        raise HTTPException(status_code=400, detail="Colour must be a 6-digit hex code, e.g. FDBE02")
    others = sum(d["weight"] for d in manager.get_dye_catalog() if d["dye_id"] != dye_id)
    if others + body.weight > 100:
        raise HTTPException(status_code=400, detail=f"All weights together can't go above 100 (the others already add up to {others:g})")
    manager.upsert_dye(
        dye_id, name, body.weight, body.hex.strip().lstrip("#").upper(),
        _discord_id(body.role_id, "Role"), _discord_id(body.emoji_id, "Emoji"),
    )
    return _catalog()


@router.delete("/catalog/{dye_id}")
async def delete_dye(dye_id: str, _=Depends(require_manage_config)):
    """Removes a dye and every player's unlock of it."""
    if not any(d["dye_id"] == dye_id for d in manager.get_dye_catalog()):
        raise HTTPException(status_code=404, detail="Unknown dye")
    removed = manager.remove_dye(dye_id)
    return {**_catalog(), "unlocks_removed": removed}
