import asyncio
import logging
import os

import aiohttp
from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from db import manager
from lib.get_uuid import get_uuid as _get_uuid_sync
from web.auth import require_auth, require_api_fetch, require_bot_control

router = APIRouter(prefix="/api/bots", tags=["bots"])

_IPC_URL = os.getenv("BOT_IPC_URL", "http://localhost:8081")
_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")
_TIMEOUT = aiohttp.ClientTimeout(total=5)
_LONG_TIMEOUT = aiohttp.ClientTimeout(total=15)

_refresh_tasks: set[str] = set()


async def _fetch_hypixel_stats(session, uuid: str) -> dict:
    _key = os.getenv("HYPIXEL_API_KEY", "")
    result = {"skyblock_level": None, "last_login": None}
    uuid_nodash = uuid.replace("-", "")
    try:
        async with session.get(
            "https://api.hypixel.net/v2/player",
            params={"uuid": uuid_nodash},
            headers={"API-Key": _key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            d = await r.json()
            if d.get("success") and d.get("player"):
                result["last_login"] = d["player"].get("lastLogin")
    except Exception:
        pass
    try:
        async with session.get(
            "https://api.hypixel.net/v2/skyblock/profiles",
            params={"uuid": uuid_nodash},
            headers={"API-Key": _key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            d = await r.json()
            if d.get("success") and d.get("profiles"):
                highest = max(
                    (p.get("members", {}).get(uuid_nodash, {}).get("leveling", {}).get("experience", 0)
                     for p in d["profiles"]),
                    default=0,
                )
                if highest > 0:
                    result["skyblock_level"] = round(highest / 100, 1)
    except Exception:
        pass
    return result


async def _do_refresh_stats(key: str) -> None:
    _refresh_tasks.add(key)
    try:
        rows = manager.get_guild_members_with_uuid(key)
        async with aiohttp.ClientSession() as session:
            for ign, uuid in rows:
                if not uuid:
                    uuid = await asyncio.to_thread(_get_uuid_sync, ign)
                    if uuid:
                        manager.update_guild_member_uuid(key, ign, uuid)
                if uuid:
                    stats = await _fetch_hypixel_stats(session, uuid)
                    manager.update_guild_member_stats(key, ign, stats["skyblock_level"], stats["last_login"])
                await asyncio.sleep(1.0)  # ~60 req/min, well under 300/5min limit
    except Exception as e:
        logging.error(f"Stats refresh for {key} failed: {e}")
    finally:
        _refresh_tasks.discard(key)


def _headers():
    return {"X-IPC-Secret": _IPC_SECRET} if _IPC_SECRET else {}


def _offline_status():
    return {
        key: {
            "key": key,
            "name": config.display_name,
            "short_name": config.short_name,
            "username": config.mc_username,
            "connected": False,
        }
        for key, config in GUILD_CONFIGS.items()
    }


@router.get("")
async def get_bots(_=Depends(require_bot_control)):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{_IPC_URL}/status", headers=_headers(), timeout=_TIMEOUT) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
    return _offline_status()


@router.get("/{key}/overview")
async def get_guild_overview(key: str, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{_IPC_URL}/guild/{key}/overview", headers=_headers(), timeout=_TIMEOUT) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{_IPC_URL}/guild/{key}/members", headers=_headers(), timeout=_LONG_TIMEOUT) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise HTTPException(status_code=resp.status, detail="IPC error")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot process is offline")


@router.post("/{key}/restart")
async def restart_bot(key: str, _=Depends(require_bot_control)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown bot key")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{_IPC_URL}/restart/{key}", headers=_headers(), timeout=_LONG_TIMEOUT) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise HTTPException(status_code=resp.status, detail="IPC error")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot process is offline")


@router.post("/{key}/stop")
async def stop_bot(key: str, _=Depends(require_bot_control)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown bot key")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{_IPC_URL}/stop/{key}", headers=_headers(), timeout=_LONG_TIMEOUT) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise HTTPException(status_code=resp.status, detail="IPC error")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot process is offline")


@router.post("/{key}/refresh-stats")
async def refresh_guild_stats(key: str, _=Depends(require_api_fetch)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    if key in _refresh_tasks:
        return {"status": "already_running", "total": 0}
    rows = manager.get_guild_members_with_uuid(key)
    asyncio.create_task(_do_refresh_stats(key))
    return {"status": "started", "total": len(rows)}


@router.get("/{key}/stats-status")
async def get_stats_status(key: str, _=Depends(require_api_fetch)):
    return {"fetching": key in _refresh_tasks}
