import os
import time

import aiohttp

from constants import MAYOR_XP_MULTIPLIERS

_BASE = "https://api.hypixel.net/v2"

_MAYOR_TTL = 600
_mayor_cache: tuple[float, float] | None = None


def _key() -> str:
    return os.getenv("HYPIXEL_API_KEY", "")


async def fetch_member_stats(session: aiohttp.ClientSession, uuid: str) -> dict:
    """Fetch player last_login and highest Skyblock level for a UUID.

    Records each API call in the DB. Returns {"skyblock_level": float|None, "last_login": int|None}.
    """
    from db import manager

    uuid_clean = uuid.replace("-", "")
    result: dict = {"skyblock_level": None, "last_login": None}

    try:
        async with session.get(
            f"{_BASE}/player",
            params={"uuid": uuid_clean},
            headers={"API-Key": _key()},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            d = await r.json()
            success = bool(d.get("success"))
            manager.record_api_call("/v2/player", success)
            if success and d.get("player"):
                result["last_login"] = d["player"].get("lastLogin")
    except Exception:
        pass

    try:
        async with session.get(
            f"{_BASE}/skyblock/profiles",
            params={"uuid": uuid_clean},
            headers={"API-Key": _key()},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            d = await r.json()
            success = bool(d.get("success"))
            manager.record_api_call("/v2/skyblock/profiles", success)
            if success and d.get("profiles"):
                highest = max(
                    (
                        p.get("members", {}).get(uuid_clean, {}).get("leveling", {}).get("experience", 0)
                        for p in d["profiles"]
                    ),
                    default=0,
                )
                if highest > 0:
                    result["skyblock_level"] = round(highest / 100, 1)
    except Exception:
        pass

    return result


async def fetch_mayor_multiplier() -> float:
    """Dungeon XP multiplier granted by the current SkyBlock mayor, 1.0 if none applies.

    /v2/resources/* needs no API key and doesn't count against the 300/5min budget, but the
    election only changes every few days, so the result is cached for 10 minutes anyway.
    A failed lookup isn't cached — it just falls back to 1.0 for this call.
    """
    global _mayor_cache

    now = time.time()
    if _mayor_cache and now - _mayor_cache[1] < _MAYOR_TTL:
        return _mayor_cache[0]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BASE}/resources/skyblock/election",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                d = await r.json()
        if not d.get("success"):
            return 1.0
        name = str((d.get("mayor") or {}).get("name", "")).lower()
    except Exception:
        return 1.0

    multiplier = MAYOR_XP_MULTIPLIERS.get(name, 1.0)
    _mayor_cache = (multiplier, now)
    return multiplier


async def fetch_key_info() -> dict:
    """Fetch API key usage stats from Hypixel (queriesInPastMinute, totalQueries, limit)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.hypixel.net/key",
                headers={"API-Key": _key()},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                d = await r.json()
                if d.get("success") and d.get("record"):
                    rec = d["record"]
                    return {
                        "queries_in_past_minute": rec.get("queriesInPastMinute", 0),
                        "total_queries": rec.get("totalQueries", 0),
                        "limit": rec.get("limit", 300),
                    }
    except Exception:
        pass
    return {}
