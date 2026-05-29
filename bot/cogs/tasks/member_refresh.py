import asyncio
import logging

import aiohttp
import discord
from discord.ext import commands, tasks

from db import manager
from lib.get_uuid import get_uuid
from lib.hypixel import fetch_member_stats

# Budget: ~150 of 300 requests per 500 min for background = 0.3 req/min
# Each member needs 2 calls → process 1 member every 400 seconds
_MEMBER_INTERVAL = 400


class MemberRefreshTask(commands.Cog):
    """Background cog that continually refreshes guild member stats one at a time."""

    def __init__(self, client):
        self.__cog_name__ = "member_refresh"
        super().__init__()
        self.client = client
        self._refresh_loop.start()

    def cog_unload(self):
        self._refresh_loop.cancel()

    @tasks.loop(seconds=_MEMBER_INTERVAL)
    async def _refresh_loop(self):
        row = manager.get_oldest_stats_member()
        if not row:
            return

        guild_key, ign, uuid = row
        try:
            if not uuid:
                uuid = await asyncio.to_thread(get_uuid, ign)
                if uuid:
                    manager.update_guild_member_uuid(guild_key, ign, uuid)
                else:
                    # Mark stats_fetched_at so this member moves to the back
                    manager.update_guild_member_stats(guild_key, ign, None, None)
                    return

            async with aiohttp.ClientSession() as session:
                stats = await fetch_member_stats(session, uuid)

            manager.update_guild_member_stats(
                guild_key, ign, stats["skyblock_level"], stats["last_login"]
            )
            logging.debug(f"[refresh] {guild_key}/{ign}: level={stats['skyblock_level']}")
        except Exception as e:
            logging.warning(f"[refresh] Failed for {guild_key}/{ign}: {e}")
            # Still update timestamp so this member rotates to back and doesn't block
            try:
                manager.update_guild_member_stats(guild_key, ign, None, None)
            except Exception:
                pass

    @_refresh_loop.before_loop
    async def _before_refresh(self):
        await self.client.wait_until_ready()
        # Stagger startup by 60 seconds so the bot is fully settled
        await asyncio.sleep(60)


async def setup(client):
    await client.add_cog(MemberRefreshTask(client))
