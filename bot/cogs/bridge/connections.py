import asyncio
import logging
import threading
import discord
import requests as _requests
from asyncio import run_coroutine_threadsafe
from discord.ext import commands
from javascript import Once, On
from config import GuildConfig, API_KEY
from db import manager
from lib.get_username import get_username


def _sync_guild_members_from_api(config: GuildConfig) -> None:
    """Fetch guild members from Hypixel API and sync to DB. Runs in a background thread."""
    try:
        resp = _requests.get(
            "https://api.hypixel.net/v2/guild",
            params={"name": config.guild_name},
            headers={"API-Key": API_KEY},
            timeout=15,
        )
        data = resp.json()
        if not data.get("success") or not data.get("guild"):
            logging.warning(f"[{config.short_name}] Hypixel guild API returned no data")
            return
        raw_members = data["guild"].get("members", [])
        members = []
        for m in raw_members:
            uuid = m.get("uuid", "")
            rank = m.get("rank", "")
            if not uuid:
                continue
            ign = get_username(uuid)
            if ign:
                members.append({"ign": ign, "rank": rank})
        if members:
            manager.sync_guild_members(config.key, members)
            logging.info(f"[{config.short_name}] Synced {len(members)} members from Hypixel API")
    except Exception as e:
        logging.error(f"[{config.short_name}] Hypixel guild sync failed: {e}")


class GuildConnections(commands.Cog):
    """Handles Mineflayer spawn/disconnect events for one guild."""

    def __init__(self, client, config: GuildConfig):
        self.__cog_name__ = f"{config.key}_connections"
        super().__init__()
        self.client = client
        self.config = config
        state = self.client.guilds_state[config.key]

        @Once(state.bot, "spawn")
        def on_spawn(this):
            state.connected = True
            logging.info(f"[{config.short_name}] Connected to {config.mc_options['host']}")
            threading.Thread(target=_sync_guild_members_from_api, args=(config,), daemon=True).start()
            embed = discord.Embed(
                description=f"**{config.short_name} Bridge Connected to:** `{config.mc_options['host']}`",
                color=discord.Color.dark_green(),
            )
            self.client.bridge.send(embed=embed)

        @On(state.bot, "end")
        def on_end(this, event) -> None:
            state.connected = False
            if state.manual_stop:
                state.manual_stop = False
                logging.info(f"[{config.short_name}] Manually stopped — not reconnecting")
                embed = discord.Embed(
                    description=f"**{config.short_name} Bridge stopped manually.**",
                    color=discord.Color.dark_gray(),
                )
                self.client.bridge.send(embed=embed)
                return

            logging.info(f"[{config.short_name}] Disconnected — reconnecting in 5s")
            embed = discord.Embed(
                description=(
                    f"**{config.short_name} Bridge Disconnected from:** `{config.mc_options['host']}`\n"
                    f"Reconnecting in 5 seconds..."
                ),
                color=discord.Color.orange(),
            )
            self.client.bridge.send(embed=embed)

            async def reconnect():
                await asyncio.sleep(5)
                await self.client.start_mineflayer(restart=True, account=config.key)

            run_coroutine_threadsafe(reconnect(), self.client.loop)


async def setup(client):
    for config in client.guild_configs.values():
        await client.add_cog(GuildConnections(client, config))
