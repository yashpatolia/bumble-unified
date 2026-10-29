"""`.warpout <ign>`: party a player and `/p warp` them to a bot that is sitting in SkyBlock.

Needs a bot on a SkyBlock-capable version (26.1+, see cogs/bridge/skyblock.py); bots on the
1.8.9 fallback can't be in SkyBlock, so the command refuses there."""
import asyncio
import logging
import re

from cogs.bridge.skyblock import supports_skyblock
from lib.chat_wait import wait_for_chat

_IGN_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
_INVITE_TIMEOUT = 60   # Hypixel party invites expire after 60s
_REPLY_TIMEOUT = 5     # how long to wait for Hypixel to answer a command
_WARP_TIMEOUT = 10

# Lines Hypixel sends when /p invite fails outright.
_INVITE_FAILURES = {
    "Couldn't find a player with that name!": "Couldn't find a player named {ign}",
    "You cannot invite that player since they're not online.": "{ign} isn't online",
    "You cannot invite that player.": "{ign} isn't accepting party invites",
}


def _pick_bot(client, config):
    """The bot to warp to: this guild's if it can be in SkyBlock, otherwise any that can."""
    states = [client.guilds_state[config.key]] if config else []
    states += [s for s in client.guilds_state.values() if s not in states]
    for state in states:
        if state.bot and state.connected and supports_skyblock(state.version):
            return state
    return None


async def warpout(client, config, ign: str) -> str:
    """Runs the whole invite → warp → disband flow and returns the text to reply with."""
    if not _IGN_RE.match(ign):
        return f"'{ign}' isn't a valid Minecraft username"
    state = _pick_bot(client, config)
    if state is None:
        return "Warpout needs a bot on Minecraft 26.1+ in SkyBlock, and none is connected right now"
    if state.warpout_lock.locked():
        return "Already warping someone, try again in a minute"

    async with state.warpout_lock:
        lowered = ign.lower()
        bot = state.bot
        try:
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
            bot.chat(f"/p invite {ign}")

            reply = await invite_reply
            if reply in _INVITE_FAILURES:
                joined.cancel()
                return _INVITE_FAILURES[reply].format(ign=ign)
            if reply is None:
                joined.cancel()
                bot.chat("/p disband")
                return "Hypixel didn't answer the party invite, try again"

            result = await joined
            if result is None or "has expired" in result:
                bot.chat("/p disband")
                return f"{ign} didn't accept the party invite in time"

            warped = asyncio.ensure_future(wait_for_chat(
                state,
                lambda m: lowered in m.lower() and ("warp" in m.lower() or "summon" in m.lower()),
                _WARP_TIMEOUT,
            ))
            bot.chat("/p warp")
            warp_line = await warped
            bot.chat("/p disband")
            if warp_line is None:
                return f"Sent the party warp for {ign}, but Hypixel didn't confirm it"
            return f"Warped {ign} out"
        except Exception as e:
            logging.exception(e)
            try:
                bot.chat("/p disband")
            except Exception:
                pass
            return "Something went wrong running warpout"
