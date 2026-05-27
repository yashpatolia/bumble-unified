import math
import discord
from discord.ext import commands
from discord import app_commands
from config import BK_STAFF_ROLE, BU_STAFF_ROLE, BOT_ROLE
from player import skyblock
from typing import Literal


class Apply(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="apply", description="Apply for a Bumble guild")
    @app_commands.describe(ign="Your Minecraft username", guild="Target guild")
    async def apply(self, interaction: discord.Interaction, ign: str, guild: Literal["Kindergarten", "University"]) -> None:
        await interaction.response.defer()

        player = skyblock.Player(username=ign)
        skyblock_level, _ = player.level.highest

        category = discord.utils.get(interaction.guild.categories, name="applications")
        staff_role_id = BK_STAFF_ROLE if guild == "Kindergarten" else BU_STAFF_ROLE
        staff_role = interaction.guild.get_role(staff_role_id)
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
        await channel.send(f"{staff_role.mention} — New application from **{player.username}** (Level: {skyblock_level:.1f})")


async def setup(client):
    await client.add_cog(Apply(client))
