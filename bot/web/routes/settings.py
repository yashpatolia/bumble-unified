"""Shared, not per-guild, settings on the Config page: .warpout and the extra censored chat
words. Anyone signed in can read them; changing them needs Manage Config (or admin).
Per-guild settings are in web/routes/guild_config.py."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import GUILD_CONFIGS
from db import manager
from lib import shared_settings
from web.auth import require_auth, require_manage_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsBody(BaseModel):
    warpout: Optional[dict] = None
    censor_words: Optional[list[str]] = None


def _view() -> dict:
    rows = [manager.get_setting(k) for k in ("warpout", "censor")]
    latest = max((r for r in rows if r and r["updated_at"]), key=lambda r: r["updated_at"], default=None)
    return {
        "warpout": shared_settings.get_warpout(),
        "warpout_defaults": shared_settings.WARPOUT_DEFAULTS,
        "censor_words": shared_settings.get_censor_words(),
        "guilds": [{"key": c.key, "name": c.display_name} for c in GUILD_CONFIGS.values()],
        "updated_by": latest["updated_by"] if latest else None,
        "updated_at": latest["updated_at"].isoformat() if latest else None,
    }


@router.get("")
async def get_settings(_=Depends(require_auth)):
    return _view()


@router.put("")
async def update_settings(body: SettingsBody, claims=Depends(require_manage_config)):
    try:
        warpout = None if body.warpout is None else shared_settings.validate_warpout(body.warpout, GUILD_CONFIGS.keys())
        censor = None if body.censor_words is None else shared_settings.validate_censor(body.censor_words)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    name = claims.get("name", "unknown")
    if warpout is not None:
        manager.set_setting("warpout", warpout, name)
        shared_settings.invalidate("warpout")
    if censor is not None:
        manager.set_setting("censor", censor, name)
        shared_settings.invalidate("censor")
    return _view()
