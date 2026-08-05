import discord
from discord.ext import commands
from discord import app_commands
from config import EXEC_ROLE, GUILD_CONFIGS


class Exec(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def _run_exec(self, interaction: discord.Interaction, key: str, command: str) -> None:
        config = GUILD_CONFIGS[key]
        self.client.guilds_state[key].bot.chat(f"/{command}")
        embed = discord.Embed(
            colour=discord.Colour.green(),
            description=f"**[{config.short_name}] Command Executed:** `/{command}`",
        )
        await interaction.response.send_message(embed=embed)

    # Discord requires distinct command names per guild, so these two entry
    # points stay, but both just delegate to _run_exec.

    @app_commands.command(name="bk-exec", description="Execute a command on the Bumble Kindergarten Minecraft bot")
    @app_commands.describe(command="Command to run (without the leading /)")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def bk_exec(self, interaction: discord.Interaction, command: str) -> None:
        await self._run_exec(interaction, "bk", command)

    @app_commands.command(name="bu-exec", description="Execute a command on the Bumble University Minecraft bot")
    @app_commands.describe(command="Command to run (without the leading /)")
    @app_commands.checks.has_role(EXEC_ROLE)
    async def bu_exec(self, interaction: discord.Interaction, command: str) -> None:
        await self._run_exec(interaction, "bu", command)


async def setup(client):
    await client.add_cog(Exec(client))
