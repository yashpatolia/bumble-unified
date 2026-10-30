import asyncio
import math

import discord
from discord.ext import commands
from discord import app_commands
from config import BOT_ROLE, GUILD_CONFIGS
from db import manager
from lib.guild_settings import get_rank_requirements
from player import skyblock
from player.skyblock import HypixelAPIError, PlayerNotFoundError
from typing import Literal

_GUILD_KEYS = {"Kindergarten": "bk", "University": "bu"}


def _rank_check(config, level: float) -> tuple[str, str]:
    """(where the applicant would land, what is left to the next rank) against the guild's live
    rank requirements. A level must be above a rank's number to hold it, like the auto-ranker."""
    ranks = get_rank_requirements(config)
    label = {bot_rank: hypixel_rank for hypixel_rank, bot_rank in config.discord_rank_map.items()}
    earned = [r for r, req in ranks.items() if req < level]
    first = next(iter(ranks))
    if earned:
        verdict = f"Would hold **{label.get(earned[-1], earned[-1])}**"
    else:
        verdict = f"Not above the **{label.get(first, first)}** requirement (level {ranks[first]}), so they would join at the starting rank"
    upcoming = next(((r, req) for r, req in ranks.items() if req >= level), None)
    if upcoming is None:
        return verdict, "Already above every rank requirement."
    r, req = upcoming
    return verdict, f"**{label.get(r, r)}** needs level above {req} ({max(req - level, 0):.1f} to go)"


def _stats_embed(config, player: skyblock.Player, level: float) -> discord.Embed:
    verdict, next_up = _rank_check(config, level)
    embed = discord.Embed(colour=discord.Colour.blurple(), title=f"{player.username}: stats check for {config.short_name}")
    embed.add_field(name="Skyblock level", value=f"{level:.2f}", inline=True)
    embed.add_field(name="Catacombs", value=f"{player.catacombs.level:.2f}", inline=True)
    embed.add_field(name="Slayers", value=player.slayers.levels, inline=True)
    embed.add_field(name="Rank check", value=f"{verdict}\n{next_up}", inline=False)
    current = manager.get_guild_key_for_ign(player.username)
    if current:
        embed.set_footer(text=f"Already in the {GUILD_CONFIGS[current].short_name} guild per the roster")
    return embed


class Apply(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="apply", description="Apply for a Bumble guild")
    @app_commands.describe(ign="Your Minecraft username", guild="Target guild")
    async def apply(self, interaction: discord.Interaction, ign: str, guild: Literal["Kindergarten", "University"]) -> None:
        await interaction.response.defer()

        config = GUILD_CONFIGS[_GUILD_KEYS[guild]]
        try:
            player = await asyncio.to_thread(skyblock.Player, username=ign)
        except PlayerNotFoundError:
            await interaction.edit_original_response(
                embed=discord.Embed(colour=discord.Colour.dark_red(), description=f"No Minecraft account named `{ign}`.")
            )
            return
        except HypixelAPIError as e:
            await interaction.edit_original_response(
                embed=discord.Embed(colour=discord.Colour.dark_red(), description=f"Could not read your Skyblock profile right now ({e}). Try again in a minute.")
            )
            return
        skyblock_level, _ = player.level.highest

        category = discord.utils.get(interaction.guild.categories, name="applications")
        staff_role = interaction.guild.get_role(config.staff_role_id)
        bot_role = interaction.guild.get_role(BOT_ROLE)

        overwrites = {
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            bot_role: discord.PermissionOverwrite(read_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"{ign.lower()}-{math.floor(skyblock_level)}-app",
            category=category,
            overwrites=overwrites,
        )

        embed = discord.Embed(
            colour=discord.Colour.dark_red(),
            description=f"Application ticket created: {channel.mention}",
        )
        await interaction.edit_original_response(embed=embed)
        await channel.send(
            f"{staff_role.mention} New application from **{player.username}** (Level: {skyblock_level:.1f})",
            embed=_stats_embed(config, player, skyblock_level),
        )


async def setup(client):
    await client.add_cog(Apply(client))
