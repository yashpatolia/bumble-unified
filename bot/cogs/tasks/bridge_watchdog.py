import asyncio
import logging
import os
import subprocess
import sys

from discord.ext import commands, tasks

from lib.offload import stalled_lanes

_PROBE_INTERVAL_SECONDS = 30
_PROBE_TIMEOUT_SECONDS = 25   # JSPyBridge gives up on a single call after ~10s
_FAILED_ROUNDS_BEFORE_EXIT = 3
_LANE_STALL_WARN_SECONDS = 60


class BridgeWatchdog(commands.Cog):
    """Restarts the bot process when the Python<->Node bridge wedges.

    When JSPyBridge's loop thread stalls, every Mineflayer call times out ("Timed out accessing
    'chat'") but the Python process stays alive, so pm2 never restarts it and the bridge stays
    dead until someone does it by hand. This probes each bot with a cheap property read; if every
    probed bot fails several rounds in a row it exits, and pm2 starts a fresh process."""

    def __init__(self, client):
        self.__cog_name__ = "bridge_watchdog"
        super().__init__()
        self.client = client
        self._failed_rounds = 0
        self._probe_loop.start()

    def cog_unload(self):
        self._probe_loop.cancel()

    @staticmethod
    def _probe(bot) -> None:
        bot.username  # a property read round-trips through the bridge; raises "Timed out accessing" when wedged

    @tasks.loop(seconds=_PROBE_INTERVAL_SECONDS)
    async def _probe_loop(self):
        for lane, task, seconds in stalled_lanes(_LANE_STALL_WARN_SECONDS):
            logging.warning(f"[watchdog] offload lane {lane} has been stuck in {task} for {seconds:.0f}s")

        bots = [
            (key, state.bot) for key, state in self.client.guilds_state.items()
            if state.bot and not state.manual_stop
        ]
        if not bots:
            return

        results = await asyncio.gather(
            *(asyncio.wait_for(asyncio.to_thread(self._probe, bot), _PROBE_TIMEOUT_SECONDS) for _, bot in bots),
            return_exceptions=True,
        )
        failed = [key for (key, _), result in zip(bots, results) if isinstance(result, BaseException)]

        if len(failed) < len(bots):
            if self._failed_rounds:
                logging.info("[watchdog] bridge responding again")
            self._failed_rounds = 0
            return

        self._failed_rounds += 1
        logging.warning(
            f"[watchdog] bridge probe failed for {', '.join(failed)} "
            f"({self._failed_rounds}/{_FAILED_ROUNDS_BEFORE_EXIT})"
        )
        if self._failed_rounds >= _FAILED_ROUNDS_BEFORE_EXIT:
            self._exit()

    def _exit(self) -> None:
        logging.critical("[watchdog] Python<->Node bridge is unresponsive, exiting so pm2 restarts the bot")
        # JSPyBridge leaves its Node child running when Python exits; kill it so restarts don't pile up
        # orphaned Mineflayer processes still holding the bot accounts' connections.
        if sys.platform != "win32":
            try:
                subprocess.run(["pkill", "-P", str(os.getpid())], timeout=5)
            except Exception:
                pass
        logging.shutdown()
        os._exit(1)

    @_probe_loop.before_loop
    async def _before_probe(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(120)  # let the bots log in before judging them


async def setup(client):
    await client.add_cog(BridgeWatchdog(client))
