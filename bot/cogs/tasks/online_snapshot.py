import asyncio
import logging

from discord.ext import commands, tasks

from db import manager
from lib.guild_list import parse_online_igns

_SNAPSHOT_INTERVAL_MINUTES = 10


class OnlineSnapshotTask(commands.Cog):
    """Records how many members are online per guild every few minutes (feeds the panel's activity graph)."""

    def __init__(self, client):
        self.__cog_name__ = "online_snapshot"
        super().__init__()
        self.client = client
        self._snapshot_loop.start()

    def cog_unload(self):
        self._snapshot_loop.cancel()

    @tasks.loop(minutes=_SNAPSHOT_INTERVAL_MINUTES)
    async def _snapshot_loop(self):
        for key in self.client.guild_configs:
            state = self.client.guilds_state[key]
            if not state.connected or not state.bot:
                continue
            try:
                # Shares state.list_lock with the panel members endpoint and the
                # Discord /guild list|online commands so buffers never interleave.
                async with state.list_lock:
                    state.guild_online.clear()
                    state.save_guild_online = True
                    state.bot.chat("/guild online")
                    await asyncio.sleep(1.5)
                    state.save_guild_online = False
                    online = parse_online_igns(list(state.guild_online))
                manager.record_online_snapshot(key, len(online))
            except Exception as e:
                logging.warning(f"[online_snapshot] Failed for {key}: {e}")

    @_snapshot_loop.before_loop
    async def _before_snapshot(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(90)


async def setup(client):
    await client.add_cog(OnlineSnapshotTask(client))
