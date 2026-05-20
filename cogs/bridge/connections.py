import asyncio
import logging
import discord
from asyncio import run_coroutine_threadsafe
from discord.ext import commands
from javascript import Once, On
from config import GuildConfig


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
            logging.info(f"[{config.short_name}] Connected to {config.mc_options['host']}")
            embed = discord.Embed(
                description=f"**{config.short_name} Bridge Connected to:** `{config.mc_options['host']}`",
                color=discord.Color.dark_green(),
            )
            self.client.bridge.send(embed=embed)

        @On(state.bot, "end")
        def on_end(this, event) -> None:
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
