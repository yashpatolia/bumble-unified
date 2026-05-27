import logging
import discord
from discord.ext import commands
from discord import app_commands
from config import BK_STAFF_ROLE, BU_STAFF_ROLE
from db import manager
from typing import Optional


class User(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="user", description="Look up a linked Discord-Minecraft account")
    @app_commands.describe(member="Discord member", ign="Minecraft username")
    @app_commands.checks.has_any_role(BK_STAFF_ROLE, BU_STAFF_ROLE)
    async def user(self, interaction: discord.Interaction, member: Optional[discord.Member] = None, ign: Optional[str] = None) -> None:
        await interaction.response.defer()
        try:
            if member is not None:
                result = manager.get_user_by_discord(member.id)
            elif ign is not None:
                result = manager.get_user_by_ign(ign)
            else:
                await interaction.edit_original_response(
                    embed=discord.Embed(colour=discord.Colour.dark_red(), description="Provide a member or IGN.")
                )
                return

            if result is None:
                embed = discord.Embed(colour=discord.Colour.dark_red(), description="User is not linked.")
            else:
                user_ign, discord_name, uuid = result
                embed = discord.Embed(
                    colour=discord.Colour.dark_teal(),
                    description=f"**Discord:** {discord_name}\n**UUID:** `{uuid}`\n**IGN:** {user_ign}",
                )
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            logging.error(e)


async def setup(client):
    await client.add_cog(User(client))
