import asyncio
import json
import logging
import time
from asyncio import run_coroutine_threadsafe
from discord.ext import commands
from javascript import On
from config import GuildConfig

# Hypixel only lets 26.1+ clients into SkyBlock ("You must be using Minecraft Version 26.1
# or later to play SkyBlock!").
_MIN_SKYBLOCK_VERSION = (26, 1)
# How long after a world change to ask /locraw where we ended up.
_LOCRAW_DELAY = 3
# After a failed join ("You were kicked while joining that server!" / "You tried to rejoin
# too fast") Hypixel refuses another /skyblock for a while.
_REJOIN_COOLDOWN = 60

_JOIN_FAILED = ("You were kicked while joining that server!", "You tried to rejoin too fast")


def supports_skyblock(version: str) -> bool:
    try:
        return tuple(int(p) for p in version.split(".")[:2]) >= _MIN_SKYBLOCK_VERSION
    except ValueError:
        return False


class GuildSkyblock(commands.Cog):
    """Keeps one guild's bot in SkyBlock when it runs a version Hypixel allows there.

    Hypixel moves bots between servers on its own (lobby restarts, AFK, getting kicked off
    SkyBlock), so after every world change the bot checks /locraw and sends /skyblock if it
    isn't there. Inert on FALLBACK_VERSION (1.8.9)."""

    def __init__(self, client, config: GuildConfig):
        self.__cog_name__ = f"{config.key}_skyblock"
        super().__init__()
        self.client = client
        self.config = config
        state = self.client.guilds_state[config.key]
        if not supports_skyblock(state.version):
            return

        self._retry_after = 0.0
        self._retry_scheduled = False

        def send(command: str) -> None:
            try:
                state.bot.chat(command)
            except Exception as e:
                logging.warning(f"[{config.short_name}] Failed to send {command}: {e}")

        async def check_location_later():
            await asyncio.sleep(_LOCRAW_DELAY)
            send("/locraw")

        async def retry_join_later():
            await asyncio.sleep(max(0.0, self._retry_after - time.time()))
            self._retry_scheduled = False
            send("/skyblock")

        def join_skyblock() -> None:
            if time.time() < self._retry_after:
                if not self._retry_scheduled:
                    self._retry_scheduled = True
                    run_coroutine_threadsafe(retry_join_later(), self.client.loop)
                return
            logging.info(f"[{config.short_name}] Not in SkyBlock, sending /skyblock")
            send("/skyblock")

        @On(state.bot, "spawn")
        def on_spawn(this):
            run_coroutine_threadsafe(check_location_later(), self.client.loop)

        @On(state.bot, "messagestr")
        def on_messagestr(this, message, *args):
            if not message:
                return
            if message.startswith('{"server"'):
                try:
                    location = json.loads(message)
                except ValueError:
                    return
                if location.get("gametype") != "SKYBLOCK":
                    join_skyblock()
            elif any(phrase in message for phrase in _JOIN_FAILED):
                logging.info(f"[{config.short_name}] SkyBlock join refused, retrying in {_REJOIN_COOLDOWN}s")
                self._retry_after = time.time() + _REJOIN_COOLDOWN
                join_skyblock()


async def setup(client):
    for config in client.guild_configs.values():
        await client.add_cog(GuildSkyblock(client, config))
