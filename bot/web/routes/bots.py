import os

import aiohttp
from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from web.auth import require_auth, require_bot_control

router = APIRouter(prefix="/api/bots", tags=["bots"])

_IPC_URL = os.getenv("BOT_IPC_URL", "http://localhost:8081")
_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")
_TIMEOUT = aiohttp.ClientTimeout(total=5)
_LONG_TIMEOUT = aiohttp.ClientTimeout(total=15)


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
