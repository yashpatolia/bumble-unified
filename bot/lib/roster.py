"""Spotting Minecraft name changes, so a renamed member keeps their roster row, history, link and
message counts instead of looking like one person who left and a stranger who joined.

Two sources catch renames:
- the background refresh, which reads the player's current name from the same Hypixel call it
  already makes (`fetch_member_stats()["name"]`), and
- `detect_renames` below, for `/guild list` results (which only carry names): a name that is not on
  the roster is looked up on Mojang and, when it belongs to a roster member's UUID, treated as that
  member's new name."""
import logging

import aiohttp

from db import manager

_MAX_LOOKUPS = 10  # per sync, so one odd list can't fire hundreds of Mojang calls


async def _mojang_uuid(session: aiohttp.ClientSession, name: str):
    try:
        async with session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{name}", timeout=aiohttp.ClientTimeout(total=5)
        ) as r:
            if r.status == 200:
                return (await r.json()).get("id")
    except Exception:
        pass
    return None


async def detect_renames(guild_key: str, parsed: list) -> int:
    """Renames roster members whose new name shows up in a fresh `/guild list` (`parsed` is
    [{"ign", "rank"}, ...]) before the roster is synced to it. Returns how many were renamed."""
    roster = manager.get_guild_members_with_uuid(guild_key)
    known = {ign.lower() for ign, _ in roster}
    listed = {m["ign"].lower() for m in parsed}
    by_uuid = {uuid.replace("-", ""): ign for ign, uuid in roster if uuid and ign.lower() not in listed}
    unknown = [m["ign"] for m in parsed if m["ign"].lower() not in known]
    if not by_uuid or not unknown:
        return 0

    renamed = 0
    async with aiohttp.ClientSession() as session:
        for name in unknown[:_MAX_LOOKUPS]:
            uuid = await _mojang_uuid(session, name)
            old = by_uuid.get(uuid) if uuid else None
            if old and manager.rename_member(guild_key, old, name, uuid):
                logging.info(f"[roster] {guild_key}: {old} is now {name}")
                renamed += 1
    return renamed
