"""
Unified guild command cogs — replaces the separate bk_guild.py and bu_guild.py files.

Both BKGuild and BUGuild need to stay as two separate GroupCog classes (Discord
requires distinct command-group names, "bk-guild"/"bu-guild", and distinct
per-guild role checks baked in at decoration time), so each still declares its
own decorated command methods. But every method body is identical apart from
which GuildState/role it acts on, so each one just forwards to a shared
`_do_*` helper below — that's the only logic that needs to change to alter
behavior for both guilds at once. Adding a third guild requires a new class
(~10 one-line methods) and a line in setup().
"""
import asyncio
import re
import discord
from discord.ext import commands
from discord import app_commands
from config import BK_STAFF_ROLE, BU_STAFF_ROLE

_FOOTER_RE = re.compile(r"-{5,}")


def _guild_list_embed(display_name: str, mc_command: str, lines: list[str]) -> discord.Embed:
    # Drop blank lines and the raw dash-only footer the game appends —
    # Discord's code block already visually separates the content.
    cleaned = [line.strip() for line in lines if line.strip() and not _FOOTER_RE.fullmatch(line.strip())]
    text = "\n".join(cleaned) or "No response received."
    title = f"{display_name} — {'Online Members' if mc_command == '/guild online' else 'Guild List'}"
    return discord.Embed(title=title, colour=discord.Colour.teal(), description=f"```{text}```")


async def _do_list_or_online(interaction: discord.Interaction, display_name: str, state, mc_command: str) -> None:
    await interaction.response.defer()
    is_online = mc_command == "/guild online"

    async with state.list_lock:
        if is_online:
            state.guild_online.clear()
            state.save_guild_online = True
        else:
            state.guild_list.clear()
            state.save_guild_list = True

        state.bot.chat(mc_command)
        await asyncio.sleep(1.5)

        if is_online:
            state.save_guild_online = False
            lines = list(state.guild_online)
            state.guild_online.clear()
        else:
            state.save_guild_list = False
            lines = list(state.guild_list)
            state.guild_list.clear()

    await interaction.edit_original_response(embed=_guild_list_embed(display_name, mc_command, lines))


async def _do_mute(interaction: discord.Interaction, state, ign: str, time: str) -> None:
    state.bot.chat(f"/guild mute {ign} {time}")
    embed = discord.Embed(colour=discord.Colour.green(), description=f"**Muted:** `{ign}` for {time}")
    await interaction.response.send_message(embed=embed)


async def _do_unmute(interaction: discord.Interaction, state, ign: str) -> None:
    state.bot.chat(f"/guild unmute {ign}")
    embed = discord.Embed(colour=discord.Colour.green(), description=f"**Unmuted:** `{ign}`")
    await interaction.response.send_message(embed=embed)


async def _do_invite(interaction: discord.Interaction, state, ign: str) -> None:
    await interaction.response.defer()
    state.bot.chat(f"/guild invite {ign}")
    await asyncio.sleep(0.75)
    embed = discord.Embed(colour=discord.Colour.teal(), description=state.guild_invite or "No response received.")
    state.guild_invite = None
    await interaction.edit_original_response(embed=embed)


async def _do_kick(interaction: discord.Interaction, state, ign: str, reason: str) -> None:
    state.bot.chat(f"/guild kick {ign} {reason}")
    embed = discord.Embed(colour=discord.Colour.green(), description=f"**Kicked:** `{ign}` — {reason}")
    await interaction.response.send_message(embed=embed)


async def _do_accept(interaction: discord.Interaction, state, ign: str) -> None:
    state.bot.chat(f"/guild accept {ign}")
    embed = discord.Embed(colour=discord.Colour.dark_green(), description=f"Accepted: `{ign}`")
    await interaction.response.send_message(embed=embed)


async def _do_promote(interaction: discord.Interaction, state, ign: str) -> None:
    state.bot.chat(f"/guild promote {ign}")
    embed = discord.Embed(colour=discord.Colour.green(), description=f"**Promoted:** `{ign}`")
    await interaction.response.send_message(embed=embed)


async def _do_demote(interaction: discord.Interaction, state, ign: str) -> None:
    state.bot.chat(f"/guild demote {ign}")
    embed = discord.Embed(colour=discord.Colour.red(), description=f"**Demoted:** `{ign}`")
    await interaction.response.send_message(embed=embed)


class BKGuild(commands.GroupCog, name="bk-guild"):
    def __init__(self, client):
        self.client = client
        self.state = client.guilds_state["bk"]
        self.display_name = client.guild_configs["bk"].display_name
        super().__init__()

    @app_commands.command(name="list", description="Lists Bumble Kindergarten members")
    async def list(self, interaction: discord.Interaction) -> None:
        await _do_list_or_online(interaction, self.display_name, self.state, "/guild list")

    @app_commands.command(name="online", description="Shows online Bumble Kindergarten members")
    async def online(self, interaction: discord.Interaction) -> None:
        await _do_list_or_online(interaction, self.display_name, self.state, "/guild online")

    @app_commands.command(name="mute", description="Mute a BK guild member")
    @app_commands.describe(ign="Player IGN", time="Duration (e.g. 10m, 2h, 1d)")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def mute(self, interaction: discord.Interaction, ign: str, time: str) -> None:
        await _do_mute(interaction, self.state, ign, time)

    @app_commands.command(name="unmute", description="Unmute a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def unmute(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_unmute(interaction, self.state, ign)

    @app_commands.command(name="invite", description="Invite a player to BK")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def invite(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_invite(interaction, self.state, ign)

    @app_commands.command(name="kick", description="Kick a player from BK")
    @app_commands.describe(ign="Player IGN", reason="Kick reason")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def kick(self, interaction: discord.Interaction, ign: str, reason: str) -> None:
        await _do_kick(interaction, self.state, ign, reason)

    @app_commands.command(name="accept", description="Accept a BK join request")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def accept(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_accept(interaction, self.state, ign)

    @app_commands.command(name="promote", description="Promote a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def promote(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_promote(interaction, self.state, ign)

    @app_commands.command(name="demote", description="Demote a BK guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BK_STAFF_ROLE)
    async def demote(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_demote(interaction, self.state, ign)


class BUGuild(commands.GroupCog, name="bu-guild"):
    def __init__(self, client):
        self.client = client
        self.state = client.guilds_state["bu"]
        self.display_name = client.guild_configs["bu"].display_name
        super().__init__()

    @app_commands.command(name="list", description="Lists Bumble University members")
    async def list(self, interaction: discord.Interaction) -> None:
        await _do_list_or_online(interaction, self.display_name, self.state, "/guild list")

    @app_commands.command(name="online", description="Shows online Bumble University members")
    async def online(self, interaction: discord.Interaction) -> None:
        await _do_list_or_online(interaction, self.display_name, self.state, "/guild online")

    @app_commands.command(name="mute", description="Mute a BU guild member")
    @app_commands.describe(ign="Player IGN", time="Duration (e.g. 10m, 2h, 1d)")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def mute(self, interaction: discord.Interaction, ign: str, time: str) -> None:
        await _do_mute(interaction, self.state, ign, time)

    @app_commands.command(name="unmute", description="Unmute a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def unmute(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_unmute(interaction, self.state, ign)

    @app_commands.command(name="invite", description="Invite a player to BU")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def invite(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_invite(interaction, self.state, ign)

    @app_commands.command(name="kick", description="Kick a player from BU")
    @app_commands.describe(ign="Player IGN", reason="Kick reason")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def kick(self, interaction: discord.Interaction, ign: str, reason: str) -> None:
        await _do_kick(interaction, self.state, ign, reason)

    @app_commands.command(name="accept", description="Accept a BU join request")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def accept(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_accept(interaction, self.state, ign)

    @app_commands.command(name="promote", description="Promote a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def promote(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_promote(interaction, self.state, ign)

    @app_commands.command(name="demote", description="Demote a BU guild member")
    @app_commands.describe(ign="Player IGN")
    @app_commands.checks.has_role(BU_STAFF_ROLE)
    async def demote(self, interaction: discord.Interaction, ign: str) -> None:
        await _do_demote(interaction, self.state, ign)


async def setup(client):
    await client.add_cog(BKGuild(client))
    await client.add_cog(BUGuild(client))
