from fastapi import APIRouter, Depends, HTTPException

from db import manager
from web.auth import require_auth

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
    row = manager.get_user_by_discord(int(claims["sub"]))
    if row is None:
        return {"linked": False}
    ign, discord_name, uuid = row
    return _build_profile(uuid, ign, discord_name or claims.get("name"), claims.get("avatar"))


@router.get("/search")
async def search_dyes(q: str = "", _=Depends(require_auth)):
    q = q.strip()
    if not q:
        return {"results": []}
    rows = manager.search_users_with_dye_counts(q, limit=20)
    return {
        "results": [
            {
                "uuid": r[0],
                "ign": r[1],
                "discord_id": str(r[2]) if r[2] else None,
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
