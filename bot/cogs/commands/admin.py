import discord
from discord.ext import commands
from discord import app_commands
from config import EXEC_ROLE
from db import manager


class AdminCommands(commands.GroupCog, name="admin"):
    def __init__(self, client):
        self.client = client
        super().__init__()

    @app_commands.command(name="add-dye", description="Add a dye to the database")
    @app_commands.describe(dye_id="Dye ID (snake_case)", dye_name="Display name", weight="Drop weight (decimal)", hex="Hex color code")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def add_dye(self, interaction: discord.Interaction, dye_id: str, dye_name: str, weight: float, hex: str) -> None:
        await interaction.response.defer()
        try:
            manager.add_dye(dye_id, dye_name, weight, hex)
            embed = discord.Embed(colour=discord.Colour.green(), description=f"**Added:** {dye_name}")
        except Exception as e:
            embed = discord.Embed(colour=discord.Colour.red(), description=str(e))
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="remove-dye", description="Remove a dye from the database")
    @app_commands.describe(dye_id="Dye ID to remove")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def remove_dye(self, interaction: discord.Interaction, dye_id: str) -> None:
        await interaction.response.defer()
        try:
            manager.remove_dye(dye_id)
            embed = discord.Embed(colour=discord.Colour.green(), description=f"**Removed:** `{dye_id}`")
        except Exception as e:
            embed = discord.Embed(colour=discord.Colour.red(), description=str(e))
        await interaction.edit_original_response(embed=embed)


async def setup(client):
    await client.add_cog(AdminCommands(client))
