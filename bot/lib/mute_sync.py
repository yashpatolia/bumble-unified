"""Mirrors a guild mute onto Discord: a muted member who has linked their Discord account is
timed out for the same duration, and the timeout is lifted again on an early unmute. Each mute is
recorded in `guild_mutes` with its real expiry, and `cogs/tasks/mute_sync.py` reconciles Discord against
those rows every minute, so a mute or unmute the bot missed while offline is still fixed afterwards.

Discord caps a timeout at 28 days, so a longer guild mute is clamped to that."""
import asyncio
import datetime
import logging
import re

import discord

from db import manager

_MAX_TIMEOUT = datetime.timedelta(days=28)
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

MUTE_RE = re.compile(r"(?:\[[^\]]+\]\s+)?\w+\s+has muted\s+(?:\[[^\]]+\]\s+)?(\w+)\s+for\s+(\d+)\s*([smhd])", re.IGNORECASE)
UNMUTE_RE = re.compile(r"(?:\[[^\]]+\]\s+)?\w+\s+has unmuted\s+(?:\[[^\]]+\]\s+)?(\w+)\s*[.!]?\s*$", re.IGNORECASE)


def parse_mute(message: str):
    """(ign, timedelta) for a "X has muted Y for 1d" line, else None. The guild-wide
    "has muted the guild chat for" line does not match."""
    m = MUTE_RE.search(message)
    if not m:
        return None
    return m.group(1), datetime.timedelta(seconds=int(m.group(2)) * _UNITS[m.group(3).lower()])


def parse_unmute(message: str):
    """The ign from a "X has unmuted Y" line, else None (the guild-wide "unmuted the guild chat" is skipped)."""
    m = UNMUTE_RE.search(message)
    if not m or m.group(1).lower() == "the":
        return None
    return m.group(1)


def _discord_id_for(guild_key: str, ign: str):
    uuid = manager.get_member_uuid(guild_key, ign)
    if not uuid:
        user = manager.get_user_by_ign(ign)  # (ign, discord_name, uuid)
        uuid = user[2] if user else None
    user = manager.get_user_by_uuid(uuid) if uuid else None  # (ign, discord_id, ...)
    return int(user[1]) if user and user[1] else None


async def set_timeout(client, guild_key: str, ign: str, until) -> None:
    """Sets the linked Discord account's timeout to end at `until` (a datetime, clamped to 28 days
    from now), or lifts it if `until` is None. Does nothing if it already matches. Never raises: a
    missing permission or an unlinked member is only logged."""
    try:
        discord_id = await asyncio.to_thread(_discord_id_for, guild_key, ign)
        if not discord_id:
            logging.info(f"[mute] {ign} has no linked Discord account, nothing to time out")
            return
        if until is not None:
            until = min(until, discord.utils.utcnow() + _MAX_TIMEOUT)
        for server in client.guilds:
            member = server.get_member(discord_id)
            if member is None:
                logging.info(f"[mute] Discord user {discord_id} ({ign}) is not in {server.name}")
                continue
            current = member.timed_out_until
            if until is None and current is None:
                continue
            if until is not None and current is not None and abs((current - until).total_seconds()) < 90:
                continue
            try:
                await member.timeout(until, reason=f"Guild {'mute' if until else 'unmute'} for {ign}")
                logging.info(f"[mute] {'Timed out ' + ign + ' until ' + str(until) if until else 'Lifted timeout for ' + ign} in {server.name}")
            except discord.Forbidden:
                logging.warning(f"[mute] Cannot time out {ign} in {server.name} (needs Moderate Members and a role above theirs)")
            except discord.HTTPException as e:
                logging.warning(f"[mute] Could not change timeout for {ign}: {e}")
    except Exception as e:
        logging.warning(f"[mute] Sync failed for {ign}: {e}")


async def on_mute(client, guild_key: str, ign: str, duration) -> None:
    logging.info(f"[mute] {ign} muted in {guild_key} for {duration}")
    try:
        await asyncio.to_thread(manager.record_mute, guild_key, ign, duration)
    except Exception as e:  # the timeout below must not depend on the record being saved
        logging.warning(f"[mute] Could not record mute for {ign}: {e}")
    await set_timeout(client, guild_key, ign, discord.utils.utcnow() + duration)


async def on_unmute(client, guild_key: str, ign: str) -> None:
    logging.info(f"[mute] {ign} unmuted in {guild_key}")
    try:
        await asyncio.to_thread(manager.clear_mute, guild_key, ign)
    except Exception as e:
        logging.warning(f"[mute] Could not clear mute for {ign}: {e}")
    await set_timeout(client, guild_key, ign, None)


async def reconcile(client) -> None:
    """Brings every Discord timeout in line with the recorded mutes: applies missing ones (a mute
    the bot saw while its Discord link was not yet set, or one past the 28 day cap), and lifts and
    forgets those that have ended."""
    now = discord.utils.utcnow()
    for guild_key, ign, expires_at in await asyncio.to_thread(manager.get_mutes):
        if expires_at <= now:
            await set_timeout(client, guild_key, ign, None)
            await asyncio.to_thread(manager.clear_mute, guild_key, ign)
        else:
            await set_timeout(client, guild_key, ign, expires_at)
