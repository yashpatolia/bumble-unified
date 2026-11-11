import asyncio
import logging

from discord.ext import commands, tasks

from lib.mute_sync import reconcile


class MuteSyncTask(commands.Cog):
    """Every minute, makes Discord timeouts match the recorded guild mutes, so a missed unmute or an
    expired mute is still cleaned up after the bot was offline."""

    def __init__(self, client):
        self.__cog_name__ = "mute_sync"
        super().__init__()
        self.client = client
        self._loop.start()

    def cog_unload(self):
        self._loop.cancel()

    @tasks.loop(minutes=1)
    async def _loop(self):
        try:
            await reconcile(self.client)
        except Exception as e:
            logging.warning(f"[mute_sync] Reconcile failed: {e}")

    @_loop.before_loop
    async def _before(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(20)


async def setup(client):
    await client.add_cog(MuteSyncTask(client))
