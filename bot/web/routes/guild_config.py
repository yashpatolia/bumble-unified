"""Per-guild settings: rank level requirements (drive auto promote/demote) and the
thresholds behind the overview's "Needs attention" list. Anyone signed in can read
them (the panel needs the attention thresholds to build the list); editing needs
Manage Config (or admin)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import GUILD_CONFIGS, VERSION
from db import manager
from lib import guild_settings
from web.auth import require_auth, require_manage_config

router = APIRouter(prefix="/api/bots", tags=["guild-config"])


class ConfigBody(BaseModel):
    ranks: dict[str, int] = {}
    attention: dict[str, int] = {}
    activity: dict[str, dict[str, int]] = {}
    minecraft_version: Optional[str] = None  # None = leave unchanged


def _guild(key: str):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    return GUILD_CONFIGS[key]


def _view(key: str) -> dict:
    config = _guild(key)
    stored = manager.get_guild_config(key) or {}
    overrides = stored.get("rank_requirements", {})
    reverse = {bot_rank: hypixel_rank for hypixel_rank, bot_rank in config.discord_rank_map.items()}
    ranks = []
    for rank, default_level in config.ranks.items():
        ranks.append({
            "key": rank,
            "label": reverse.get(rank, rank),
            "level": int(overrides.get(rank, default_level)),
            "default_level": default_level,
            "editable": True,
        })
    attention = {k: stored.get("attention", {}).get(k, d) for k, d in guild_settings.ATTENTION_DEFAULTS.items()}
    activity = {
        period: {k: stored.get("activity_tiers", {}).get(period, {}).get(k, d) for k, d in defaults.items()}
        for period, defaults in guild_settings.ACTIVITY_DEFAULTS.items()
    }
    updated_at = stored.get("updated_at")
    return {
        "ranks": ranks,
        "attention": attention,
        "attention_defaults": guild_settings.ATTENTION_DEFAULTS,
        "activity": activity,
        "activity_defaults": guild_settings.ACTIVITY_DEFAULTS,
        "minecraft_version": guild_settings.get_minecraft_version(config),
        "minecraft_version_default": VERSION,
        "minecraft_versions": list(guild_settings.MINECRAFT_VERSIONS),
        "updated_by": stored.get("updated_by"),
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


@router.get("/{key}/config")
async def get_config(key: str, _=Depends(require_auth)):
    return _view(key)


@router.put("/{key}/config")
async def update_config(key: str, body: ConfigBody, claims=Depends(require_manage_config)):
    config = _guild(key)
    try:
        ranks = guild_settings.validate_ranks(config, body.ranks)
        attention = guild_settings.validate_attention(body.attention)
        activity = guild_settings.validate_activity(body.activity)
        version = None if body.minecraft_version is None else guild_settings.validate_minecraft_version(body.minecraft_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    manager.set_guild_config(key, ranks, attention, activity, claims.get("name", "unknown"))
    if version is not None:
        # Takes effect the next time the bot is restarted (panel restart or deploy).
        manager.set_minecraft_version(key, version, claims.get("name", "unknown"))
    guild_settings.invalidate(key)
    return _view(key)
