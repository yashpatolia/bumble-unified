"""Fetches and extracts Skyblock stats needed for bingo task progress tracking."""
import logging
import aiohttp
from config import API_KEY

_HYPIXEL_PROFILES = "https://api.hypixel.net/skyblock/profiles"


async def fetch_member_data(session: aiohttp.ClientSession, uuid: str) -> dict | None:
    """Return the most-recently-played Skyblock profile member dict for a UUID, or None."""
    uuid_nodash = uuid.replace('-', '')
    try:
        async with session.get(
            _HYPIXEL_PROFILES,
            params={"key": API_KEY, "uuid": uuid_nodash},
            timeout=aiohttp.ClientTimeout(total=12),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data.get('success') or not data.get('profiles'):
                return None
            profiles = [p for p in data['profiles'] if uuid_nodash in p.get('members', {})]
            if not profiles:
                return None
            best = max(profiles, key=lambda p: p['members'][uuid_nodash].get('last_save', 0))
            return best['members'][uuid_nodash]
    except Exception as exc:
        logging.debug(f"[BingoTracker] fetch_member_data({uuid}): {exc}")
        return None


def extract_stat(member_data: dict, task_type: str, target: dict) -> float:
    """Extract the current value for a bingo task type from a profile member dict."""
    try:
        if task_type == 'skill_xp':
            skill = target.get('skill', 'farming').lower()
            return float(member_data.get(f'experience_skill_{skill}', 0) or 0)

        if task_type == 'slayer_tier':
            boss = target.get('boss', 'zombie').lower()
            tier = int(target.get('tier', 1))
            slayer = member_data.get('slayer_bosses', {}).get(boss, {})
            # Hypixel stores T1 kills as boss_kills_tier_0, T4 as boss_kills_tier_3
            return float(slayer.get(f'boss_kills_tier_{tier - 1}', 0) or 0)

        if task_type == 'dungeon_xp':
            dungeon = target.get('dungeon', 'catacombs').lower()
            return float(
                member_data.get('dungeons', {})
                .get('dungeon_types', {})
                .get(dungeon, {})
                .get('experience', 0) or 0
            )

        if task_type == 'collection':
            item = target.get('item', '').upper()
            return float(member_data.get('collection', {}).get(item, 0) or 0)

    except Exception:
        pass
    return 0.0
