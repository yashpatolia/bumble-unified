"""Eager, manual Hypixel stats refresh for a whole guild, kicked off from the
panel and independent of the background MemberRefreshTask running in the bot
process. Deliberately slower (1 req/s) since it's user-triggered and shares
the same Hypixel budget.

_refresh_tasks / _refresh_progress are process-local, in-memory state shared
between refresh_guild_stats (kicks off the task) and get_stats_status (polls
it) — they must stay together in this module."""
import asyncio
import logging

import aiohttp
from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from db import manager
from lib.get_uuid import get_uuid as _get_uuid_sync
from web.auth import require_api_fetch

router = APIRouter(prefix="/api/bots", tags=["bots"])

_refresh_tasks: set[str] = set()
_refresh_progress: dict[str, dict] = {}  # key -> {"done": int, "total": int}


async def _fetch_hypixel_stats(session, uuid: str) -> dict:
    from lib.hypixel import fetch_member_stats
    return await fetch_member_stats(session, uuid)


async def _do_refresh_stats(key: str) -> None:
    _refresh_tasks.add(key)
    try:
        rows = manager.get_guild_members_with_uuid(key)
        total = len(rows)
        _refresh_progress[key] = {"done": 0, "total": total}
        async with aiohttp.ClientSession() as session:
            for ign, uuid in rows:
                if not uuid:
                    uuid = await asyncio.to_thread(_get_uuid_sync, ign)
                    if uuid:
                        manager.update_guild_member_uuid(key, ign, uuid)
                if uuid:
                    stats = await _fetch_hypixel_stats(session, uuid)
                    manager.update_guild_member_stats(key, ign, stats["skyblock_level"], stats["last_login"])
                _refresh_progress[key]["done"] += 1
                await asyncio.sleep(1.0)  # manual refresh: ~2 calls/s per member, uses API budget quickly
    except Exception as e:
        logging.error(f"Stats refresh for {key} failed: {e}")
    finally:
        _refresh_tasks.discard(key)
        _refresh_progress.pop(key, None)


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
    progress = _refresh_progress.get(key, {})
    return {
        "fetching": key in _refresh_tasks,
        "done": progress.get("done", 0),
        "total": progress.get("total", 0),
    }
