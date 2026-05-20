import discord
from discord.ext import commands
from discord import app_commands
from constants import DYE_ROLES, DYE_EMOJIS
from db import manager
from typing import List


class Dyes(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="dyes", description="Show your unlocked dyes and select a color role")
    @app_commands.describe(dye="Choose a dye you own")
    async def dyes(self, interaction: discord.Interaction, dye: str) -> None:
        await interaction.response.defer()

        dye_info = manager.get_dye_info(dye)
        if not dye_info:
            await interaction.edit_original_response(
                embed=discord.Embed(colour=discord.Colour.dark_red(), description="Dye not found.")
            )
            return

        hex_color, dye_name = dye_info
        uuid = manager.get_uuid_by_discord(interaction.user.id)
        if uuid is None:
            await interaction.edit_original_response(
                embed=discord.Embed(colour=discord.Colour.dark_red(), description="You are not linked. Use `/link` first.")
            )
            return

        unlocked = manager.get_unlocked_dyes(uuid)
        if dye not in unlocked:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    color=discord.Color.from_str(f"#{hex_color.lower()}"),
                    description="You do not own this dye.",
                )
            )
            return

        # Swap dye roles
        for dye_id, role_id in DYE_ROLES.items():
            role = interaction.guild.get_role(role_id)
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                break
        await interaction.user.add_roles(interaction.guild.get_role(DYE_ROLES[dye]))

        embed = discord.Embed(
            color=discord.Color.from_str(f"#{hex_color.lower()}"),
            description=f"**Selected:** <:{dye}:{DYE_EMOJIS[dye]}> {dye_name}",
        )
        await interaction.edit_original_response(embed=embed)

    @dyes.autocomplete("dye")
    async def dyes_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        uuid = manager.get_uuid_by_discord(interaction.user.id)
        if uuid is None:
            return []
        unlocked = manager.get_unlocked_dyes(uuid)
        return [
            app_commands.Choice(name=d.replace("_", " ").title(), value=d)
            for d in unlocked if current.lower() in d.replace("_", " ").lower()
        ]


async def setup(client):
    await client.add_cog(Dyes(client))
