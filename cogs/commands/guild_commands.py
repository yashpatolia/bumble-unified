"""
Unified guild command cogs — replaces the separate bk_guild.py and bu_guild.py files.

Both BKGuild and BUGuild share identical logic; the per-guild differences (bot, state,
staff role) are injected from client.guilds_state at construction time. Adding a third
guild requires only a new class (≈10 lines) and a line in setup().
"""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from config import BK_STAFF_ROLE, BU_STAFF_ROLE


def _guild_list_embed(lines: list[str]) -> discord.Embed:
    text = "".join(f"{line.lstrip()}\n" for line in lines)
    return discord.Embed(colour=discord.Colour.teal(), description=f"```{text}```")


class BKGuild(commands.GroupCog, name="bk-guild"):
    def __init__(self, client):
        self.client = client
        self.state = client.guilds_state["bk"]
        super().__init__()

    @app_commands.command(name="list", description="Lists Bumble Kindergarten members")
    async def list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.state.bot.chat("/guild list")
        await asyncio.sleep(0.75)
        await interaction.edit_original_response(embed=_guild_list_embed(self.state.guild_list))
        self.state.guild_list.clear()

    @app_commands.command(name="online", description="Shows online Bumble Kindergarten members")
    async def online(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.state.bot.chat("/guild online")
        await asyncio.sleep(0.75)
        await interaction.edit_original_response(embed=_guild_list_embed(self.state.guild_list))
        self.state.guild_list.clear()

    @app_commands.command(name="mute", description="Mute a BK guild member")
    @app_commands.describe(ign="Player IGN", time="Duration (e.g. 10m, 2h, 1d)")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def mute(self, interaction: discord.Interaction, ign: str, time: str) -> None:
        self.state.bot.chat(f"/guild mute {ign} {time}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Muted:** `{ign}` for {time}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Unmute a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def unmute(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild unmute {ign}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Unmuted:** `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Invite a player to BK")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def invite(self, interaction: discord.Interaction, ign: str) -> None:
        await interaction.response.defer()
        self.state.bot.chat(f"/guild invite {ign}")
        await asyncio.sleep(0.75)
        embed = discord.Embed(colour=discord.Colour.teal(), description=self.state.guild_invite or "No response received.")
        self.state.guild_invite = None
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="kick", description="Kick a player from BK")
    @app_commands.describe(ign="Player IGN", reason="Kick reason")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def kick(self, interaction: discord.Interaction, ign: str, reason: str) -> None:
        self.state.bot.chat(f"/guild kick {ign} {reason}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Kicked:** `{ign}` — {reason}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="accept", description="Accept a BK join request")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def accept(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild accept {ign}")
        embed = discord.Embed(colour=discord.Colour.dark_green(), description=f"Accepted: `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="promote", description="Promote a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def promote(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild promote {ign}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Promoted:** `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="demote", description="Demote a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def demote(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild demote {ign}")
        embed = discord.Embed(colour=discord.Colour.red(), description=f"**Demoted:** `{ign}`")
        await interaction.response.send_message(embed=embed)


class BUGuild(commands.GroupCog, name="bu-guild"):
    def __init__(self, client):
        self.client = client
        self.state = client.guilds_state["bu"]
        super().__init__()

    @app_commands.command(name="list", description="Lists Bumble University members")
    async def list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.state.bot.chat("/guild list")
        await asyncio.sleep(0.75)
        await interaction.edit_original_response(embed=_guild_list_embed(self.state.guild_list))
        self.state.guild_list.clear()

    @app_commands.command(name="online", description="Shows online Bumble University members")
    async def online(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.state.bot.chat("/guild online")
        await asyncio.sleep(0.75)
        await interaction.edit_original_response(embed=_guild_list_embed(self.state.guild_list))
        self.state.guild_list.clear()

    @app_commands.command(name="mute", description="Mute a BU guild member")
    @app_commands.describe(ign="Player IGN", time="Duration (e.g. 10m, 2h, 1d)")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def mute(self, interaction: discord.Interaction, ign: str, time: str) -> None:
        self.state.bot.chat(f"/guild mute {ign} {time}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Muted:** `{ign}` for {time}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Unmute a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def unmute(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild unmute {ign}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Unmuted:** `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Invite a player to BU")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def invite(self, interaction: discord.Interaction, ign: str) -> None:
        await interaction.response.defer()
        self.state.bot.chat(f"/guild invite {ign}")
        await asyncio.sleep(0.75)
        embed = discord.Embed(colour=discord.Colour.teal(), description=self.state.guild_invite or "No response received.")
        self.state.guild_invite = None
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="kick", description="Kick a player from BU")
    @app_commands.describe(ign="Player IGN", reason="Kick reason")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def kick(self, interaction: discord.Interaction, ign: str, reason: str) -> None:
        self.state.bot.chat(f"/guild kick {ign} {reason}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Kicked:** `{ign}` — {reason}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="accept", description="Accept a BU join request")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def accept(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild accept {ign}")
        embed = discord.Embed(colour=discord.Colour.dark_green(), description=f"Accepted: `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="promote", description="Promote a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def promote(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild promote {ign}")
        embed = discord.Embed(colour=discord.Colour.green(), description=f"**Promoted:** `{ign}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="demote", description="Demote a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def demote(self, interaction: discord.Interaction, ign: str) -> None:
        self.state.bot.chat(f"/guild demote {ign}")
        embed = discord.Embed(colour=discord.Colour.red(), description=f"**Demoted:** `{ign}`")
        await interaction.response.send_message(embed=embed)


async def setup(client):
    await client.add_cog(BKGuild(client))
    await client.add_cog(BUGuild(client))
