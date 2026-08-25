import asyncio
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

import discord
import uvicorn
from discord import SyncWebhook
from discord.ext import commands
from javascript import require

from config import (
    TOKEN,
    BRIDGE_CHANNEL, OFFICER_CHANNEL,
    BK_LOGS_CHANNEL, BU_LOGS_CHANNEL,
    DYES_CHANNEL, MESSAGE_LOGS_CHANNEL,
    GUILD_CONFIGS,
    BOT_IPC_PORT,
    VERSION,
)

mineflayer = require("mineflayer")
skyhelper = require("skyhelper-networth")

# Minecraft 1.20.5+'s Data Components item encoding desyncs mineflayer's NBT parser on a few
# specific packets - an open upstream bug (PrismarineJS/mineflayer #3669/#3787/#3583/#3750, no
# fix as of this writing). `window_items` (inventory sync) crashed the bot a few seconds after
# spawn with "Invalid tag: N > 20"; `world_particles` throws a PartialReadError on every packet,
# flooding the logs. Both packets' mineflayer handlers (inventory.js / particle.js) already
# degrade to a harmless no-op on an unparsed body, and nothing in this codebase reads inventory
# or particle data, so making both packets opaque buffers is safe - confirmed harmless on 1.8.9
# too, so it's applied unconditionally rather than gated on MINECRAFT_VERSION.
# Set MINECRAFT_VERSION back to 1.8.9 in .env to fall back to the legacy, always-stable path.
try:
    _mc_data = require("minecraft-data")(VERSION).protocol.play.toClient.types
    _mc_data["packet_window_items"] = "restBuffer"
    _mc_data["packet_world_particles"] = "restBuffer"
except Exception as e:
    logging.warning(f"Could not apply packet compatibility patches for version {VERSION}: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class GuildState:
    """Runtime state for a single Minecraft guild bot."""
    bot: Any = None
    connected: bool = False
    guild_list: list = field(default_factory=list)
    save_guild_list: bool = False
    guild_online: list = field(default_factory=list)
    save_guild_online: bool = False
    # Serializes access to the guild_list/guild_online buffers above so a
    # Discord /guild list|online command and the web panel's IPC member sync
    # can't interleave and bleed unrelated chat into each other's response.
    list_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    guild_invite: Optional[str] = None
    logs: Optional[SyncWebhook] = None
    manual_stop: bool = False
    guild_member_count: int = 0
    recent_chat: deque = field(default_factory=lambda: deque(maxlen=50))


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.skyhelper = skyhelper
        self.guild_configs = GUILD_CONFIGS
        self.guilds_state: dict[str, GuildState] = {key: GuildState() for key in GUILD_CONFIGS}

        # Shared webhooks
        self.bridge: SyncWebhook = None   # type: ignore
        self.officer: SyncWebhook = None  # type: ignore
        self.dyes: SyncWebhook = None     # type: ignore
        self.message_logs: SyncWebhook = None  # type: ignore

    async def start_mineflayer(self, account: str = "both") -> None:
        """Create (or recreate) the raw Mineflayer bot object(s). On reconnect,
        cogs/bridge/connections.py::reload_bridge_cogs() must be called
        afterward to rebind the bridge cogs to the new bot instance — the two
        are separate steps so the initial-boot path (which loads cogs once,
        generically, in setup_hook) doesn't need to know about cog reloading
        at all."""
        for key, config in self.guild_configs.items():
            if account not in (key, "both"):
                continue
            logging.info(f"Logging in Mineflayer bot: {config.display_name} ({config.mc_username})")
            self.guilds_state[key].bot = mineflayer.createBot(config.mc_options)

    async def setup_hook(self) -> None:
        await self.start_mineflayer()

        # Per-guild log webhooks
        log_urls = {"bk": BK_LOGS_CHANNEL, "bu": BU_LOGS_CHANNEL}
        for key, url in log_urls.items():
            self.guilds_state[key].logs = SyncWebhook.from_url(url)

        # Shared webhooks
        self.bridge = SyncWebhook.from_url(BRIDGE_CHANNEL)
        self.officer = SyncWebhook.from_url(OFFICER_CHANNEL)
        self.dyes = SyncWebhook.from_url(DYES_CHANNEL)
        self.message_logs = SyncWebhook.from_url(MESSAGE_LOGS_CHANNEL)

        # Load all cog modules
        for folder in os.listdir("cogs"):
            folder_path = f"cogs/{folder}"
            if not os.path.isdir(folder_path):
                continue
            for file in os.listdir(folder_path):
                if file.endswith(".py") and file != "__init__.py":
                    await self.load_extension(f"cogs.{folder}.{file[:-3]}")

    async def on_ready(self) -> None:
        synced = await self.tree.sync()
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id}) — synced {len(synced)} commands")


async def run_bot() -> None:
    from db.migrate import run_migrations
    run_migrations(os.getenv("DATABASE_URL", ""))

    async with Client() as client:

        from bot_ipc import create_ipc_app
        ipc_app = create_ipc_app(client)
        ipc_config = uvicorn.Config(ipc_app, host="127.0.0.1", port=BOT_IPC_PORT, log_level="warning")
        ipc_server = uvicorn.Server(ipc_config)

        await asyncio.gather(
            client.start(TOKEN),
            ipc_server.serve(),
        )


asyncio.run(run_bot())
