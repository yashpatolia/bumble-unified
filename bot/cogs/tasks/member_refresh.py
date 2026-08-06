import asyncio
import logging

import aiohttp
from discord.ext import commands, tasks

from db import manager
from lib.get_uuid import get_uuid
from lib.hypixel import fetch_member_stats
from lib.rankup import guild_rank_change

# Budget: 300 req / 5 min = 60 req/min total.
# Reserve ~24 req/min for background (2 calls per member every 5 s).
# Leaves ~36 req/min for user dot-commands. Full 250-member cycle ≈ 21 min.
_MEMBER_INTERVAL = 5


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

        guild_key, ign, uuid, current_rank = row
        try:
            if not uuid:
                uuid = await asyncio.to_thread(get_uuid, ign)
                if uuid:
                    manager.update_guild_member_uuid(guild_key, ign, uuid)
                else:
                    manager.update_guild_member_stats(guild_key, ign, None, None)
                    return

            async with aiohttp.ClientSession() as session:
                stats = await fetch_member_stats(session, uuid)

            level = stats["skyblock_level"]
            manager.update_guild_member_stats(guild_key, ign, level, stats["last_login"])
            logging.debug(f"[refresh] {guild_key}/{ign}: level={level}")

            if level is None:
                return

            config = self.client.guild_configs.get(guild_key)
            if config is None:
                return

            bot_rank = config.discord_rank_map.get(current_rank)
            if bot_rank is None:
                return

            state = self.client.guilds_state[guild_key]
            if not state.bot or getattr(state.bot, "ended", True):
                return

            result = await guild_rank_change(
                bot_rank, state.bot, username=ign, uuid=uuid,
                ranks=config.ranks, send_msg=False, known_level=level,
            )
            if result and "No rank change" not in result:
                logging.info(f"[{config.short_name}] Rank update {ign}: {result}")
                # Update DB rank immediately so next cycle uses the new rank.
                # Without this, the message_handler regex may store a partial
                # rank name (e.g. "Sweaty" instead of "Sweaty Bee"), causing
                # discord_rank_map to miss it and the sync to reset to the old rank.
                required_bot_ranks = [r for r, req in config.ranks.items() if req < level]
                if required_bot_ranks:
                    reverse_rank_map = {v: k for k, v in config.discord_rank_map.items()}
                    new_hypixel_rank = reverse_rank_map.get(required_bot_ranks[-1], current_rank)
                    manager.upsert_guild_member(guild_key, ign, new_hypixel_rank)
                # Note: no separate logs embed here — the /g promote|demote command
                # triggers a real Hypixel guild-chat system message ("X was promoted
                # from Y to Z"), which message_handler.py already forwards to logs.
                # Sending our own embed too would just duplicate that line.

        except Exception as e:
            logging.warning(f"[refresh] Failed for {guild_key}/{ign}: {e}")
            try:
                manager.update_guild_member_stats(guild_key, ign, None, None)
            except Exception:
                pass

    @_refresh_loop.before_loop
    async def _before_refresh(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(60)


async def setup(client):
    await client.add_cog(MemberRefreshTask(client))
