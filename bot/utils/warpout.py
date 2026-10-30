"""`.warpout <ign>`: party a player and `/p warp` them to the warpout bot in SkyBlock.

Every warpout runs on the bot of the guild with GuildConfig.handles_warpout (BU), which
cogs/bridge/skyblock.py keeps in SkyBlock. That needs 26.1+; on the 1.8.9 fallback the bot
can't be in SkyBlock, so the command refuses. Requests run one at a time in arrival order;
anyone who has to wait is told their place in the queue straight away."""
import asyncio
import logging
import re
import time
from typing import Callable

from cogs.bridge.skyblock import supports_skyblock
from lib.chat_wait import wait_for_chat

_IGN_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
_INVITE_TIMEOUT = 60   # Hypixel party invites expire after 60s
_REPLY_TIMEOUT = 5     # how long to wait for Hypixel to answer a command
_WARP_TIMEOUT = 10
_DISBAND_ATTEMPTS = 3
_SETTLE_AFTER_WARP = 2 # Hypixel ignored a /p disband sent straight after /p warp
# Hypixel drops commands sent too close together, and the warpout bot is also relaying guild
# chat, so party commands are spaced out and a rate-limit reply makes the disband back off.
_COMMAND_GAP = 1.5
_RATE_LIMIT_BACKOFF = 3
_RATE_LIMITED = ("too fast", "slow down", "wait before")
_MAX_QUEUE = 10        # waiting + running; each warpout can take up to ~80s

# Lines Hypixel sends when /p invite fails outright.
_INVITE_FAILURES = {
    "Couldn't find a player with that name!": "Couldn't find a player named {ign}",
    "You cannot invite that player since they're not online.": "{ign} isn't online",
    "You cannot invite that player.": "{ign} isn't accepting party invites",
}


def _warpout_state(client):
    for key, config in client.guild_configs.items():
        if config.handles_warpout:
            return client.guilds_state[key]
    return None


async def warpout(client, ign: str, notify: Callable[[str], None]) -> str:
    """Queues `ign` for a warpout and returns the text to reply with once it has run.
    `notify` posts an interim reply (the queue position) while the request waits."""
    if not _IGN_RE.match(ign):
        return f"'{ign}' isn't a valid Minecraft username"
    state = _warpout_state(client)
    if state is None or not state.bot or not state.connected:
        return "The warpout bot isn't connected right now"
    if not supports_skyblock(state.version):
        return "Warpout needs the bot on Minecraft 26.1+, it's on the 1.8.9 fallback right now"

    lowered = ign.lower()
    if lowered in state.warpout_queue:
        return f"{ign} is already in the warpout queue"
    if len(state.warpout_queue) >= _MAX_QUEUE:
        return "The warpout queue is full, try again in a few minutes"

    state.warpout_queue.append(lowered)
    try:
        ahead = len(state.warpout_queue) - 1
        if ahead:
            notify(f"Queued {ign} for warpout, {ahead} ahead")
        async with state.warpout_lock:
            if not state.bot or not state.connected:
                return f"The warpout bot disconnected before {ign}'s turn, try again"
            return await _run(state, ign)
    finally:
        state.warpout_queue.remove(lowered)


async def _party_command(state, command: str) -> None:
    """Sends a /p command at least _COMMAND_GAP seconds after the previous one."""
    wait = state.last_party_command + _COMMAND_GAP - time.monotonic()
    if wait > 0:
        await asyncio.sleep(wait)
    state.bot.chat(command)
    state.last_party_command = time.monotonic()


async def _disband(state) -> bool:
    """Disbands the bot's party and waits for Hypixel to confirm it, retrying a few times.
    Also confirms when there was no party to begin with."""
    for attempt in range(_DISBAND_ATTEMPTS):
        reply = asyncio.ensure_future(wait_for_chat(
            state,
            lambda m: ("disbanded the party" in m
                       or m in ("You are not in a party right now.", "You are not currently in a party.")
                       or any(phrase in m.lower() for phrase in _RATE_LIMITED)),
            _REPLY_TIMEOUT,
        ))
        await _party_command(state, "/p disband")
        line = await reply
        if line and not any(phrase in line.lower() for phrase in _RATE_LIMITED):
            return True
        await asyncio.sleep(_RATE_LIMIT_BACKOFF if line else 0)
    logging.warning(f"Warpout: /p disband wasn't confirmed after {_DISBAND_ATTEMPTS} tries")
    return False


async def _run(state, ign: str) -> str:
    """One invite, warp, disband cycle. Caller holds state.warpout_lock."""
    lowered = ign.lower()
    try:
        # Start from an empty party even if an earlier warpout's disband didn't go through,
        # so this player isn't warped along with a leftover member (or vice versa).
        await _disband(state)

        invite_reply = asyncio.ensure_future(wait_for_chat(
            state,
            lambda m: m in _INVITE_FAILURES or ("invited" in m and lowered in m.lower()),
            _REPLY_TIMEOUT,
        ))
        joined = asyncio.ensure_future(wait_for_chat(
            state,
            lambda m: lowered in m.lower() and (m.endswith("joined the party.") or "has expired" in m),
            _INVITE_TIMEOUT + 5,
        ))
        await _party_command(state, f"/p invite {ign}")

        reply = await invite_reply
        if reply in _INVITE_FAILURES:
            joined.cancel()
            return _INVITE_FAILURES[reply].format(ign=ign)
        if reply is None:
            joined.cancel()
            await _disband(state)
            return "Hypixel didn't answer the party invite, try again"

        result = await joined
        if result is None or "has expired" in result:
            await _disband(state)
            return f"{ign} didn't accept the party invite in time"

        warped = asyncio.ensure_future(wait_for_chat(
            state,
            lambda m: lowered in m.lower() and ("warp" in m.lower() or "summon" in m.lower()),
            _WARP_TIMEOUT,
        ))
        await _party_command(state, "/p warp")
        warp_line = await warped
        await asyncio.sleep(_SETTLE_AFTER_WARP)
        await _disband(state)
        if warp_line is None:
            return f"Sent the party warp for {ign}, but Hypixel didn't confirm it"
        return f"Warped {ign} out"
    except Exception as e:
        logging.exception(e)
        try:
            await _disband(state)
        except Exception:
            pass
        return "Something went wrong running warpout"
