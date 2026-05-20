import asyncio
import logging
import os
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
    PANEL_PORT,
)
from db import manager

mineflayer = require("mineflayer")
skyhelper = require("skyhelper-networth")

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
    guild_invite: Optional[str] = None
    logs: Optional[SyncWebhook] = None
    manual_stop: bool = False


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

    async def start_mineflayer(self, restart: bool = False, account: str = "both") -> None:
        from cogs.bridge.connections import GuildConnections
        from cogs.bridge.bridge import GuildBridge
        from cogs.bridge.message_handler import GuildMessageHandler

        for key, config in self.guild_configs.items():
            if account not in (key, "both"):
                continue
            logging.info(f"Logging in Mineflayer bot: {config.display_name} ({config.mc_username})")
            self.guilds_state[key].bot = mineflayer.createBot(config.mc_options)
            if restart:
                for suffix in ("connections", "bridge", "message_handler"):
                    await self.remove_cog(f"{key}_{suffix}")
                await self.add_cog(GuildConnections(self, config))
                await self.add_cog(GuildBridge(self, config))
                await self.add_cog(GuildMessageHandler(self, config))

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
                if file.endswith(".py"):
                    await self.load_extension(f"cogs.{folder}.{file[:-3]}")

    async def on_ready(self) -> None:
        synced = await self.tree.sync()
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id}) — synced {len(synced)} commands")


async def run_bot() -> None:
    manager.setup_panel_tables()

    # Attach log handler early so startup logs are captured
    from web.logs import WebLogHandler
    logging.getLogger().addHandler(WebLogHandler())

    async with Client() as client:

        # Build the FastAPI app and start uvicorn as a second asyncio task
        from web.app import create_app
        web_app = create_app(client)
        config = uvicorn.Config(web_app, host="0.0.0.0", port=PANEL_PORT, log_level="warning")
        server = uvicorn.Server(config)

        await asyncio.gather(
            client.start(TOKEN),
            server.serve(),
        )


asyncio.run(run_bot())
