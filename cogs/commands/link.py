import discord
from discord.ext import commands
from discord import app_commands
from lib import get_uuid, fetch
from config import API_KEY
from db import manager


class Link(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="link", description="Link your Minecraft account to Discord")
    @app_commands.describe(ign="Your Minecraft username")
    async def link(self, interaction: discord.Interaction, ign: str) -> None:
        await interaction.response.defer()

        uuid = get_uuid(ign)
        data = await fetch(f"https://api.hypixel.net/v2/player?uuid={uuid}&key={API_KEY}")
        discord_name = data["player"]["socialMedia"]["links"].get("DISCORD", "")

        if discord_name != interaction.user.name:
            embed = discord.Embed(
                colour=discord.Colour.dark_red(),
                description=(
                    "Discord username mismatch.\n"
                    f"Please set your in-game Discord social link to `{interaction.user.name}`."
                ),
            )
            await interaction.edit_original_response(embed=embed)
            return

        if manager.is_linked(uuid):
            embed = discord.Embed(colour=discord.Colour.dark_green(), description="You are already linked.")
            await interaction.edit_original_response(embed=embed)
            return

        manager.link_user(uuid, ign, interaction.user.id, discord_name)

        embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            description=f"**Discord:** {discord_name}\n**IGN:** {ign}\n**UUID:** `{uuid}`",
        )
        await interaction.edit_original_response(embed=embed)


async def setup(client):
    await client.add_cog(Link(client))
