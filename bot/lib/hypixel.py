import os

import aiohttp

_BASE = "https://api.hypixel.net/v2"


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
