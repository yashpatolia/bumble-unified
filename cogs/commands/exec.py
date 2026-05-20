import discord
from discord.ext import commands
from discord import app_commands
from config import EXEC_ROLE


class Exec(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="bk-exec", description="Execute a command on the Bumble Kindergarten Minecraft bot")
    @app_commands.describe(command="Command to run (without the leading /)")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def bk_exec(self, interaction: discord.Interaction, command: str) -> None:
        self.client.guilds_state["bk"].bot.chat(f"/{command}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**[BK] Command Executed:** `/{command}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bu-exec", description="Execute a command on the Bumble University Minecraft bot")
    @app_commands.describe(command="Command to run (without the leading /)")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def bu_exec(self, interaction: discord.Interaction, command: str) -> None:
        self.client.guilds_state["bu"].bot.chat(f"/{command}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**[BU] Command Executed:** `/{command}`")
        await interaction.response.send_message(embed=embed)


async def setup(client):
    await client.add_cog(Exec(client))
