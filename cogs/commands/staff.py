import discord
from discord.ext import commands
from discord import app_commands
from config import BK_STAFF_ROLE, BU_STAFF_ROLE
from lib.get_uuid import get_uuid
from db import manager


class StaffCommands(commands.GroupCog, name="staff"):
    def __init__(self, client):
        self.client = client
        super().__init__()

    @app_commands.command(name="link", description="Forcefully link a Discord user to a Minecraft account")
    @app_commands.describe(member="Discord member to link", ign="Minecraft username")
    @app_commands.checks.has_any_role(BK_STAFF_ROLE, BU_STAFF_ROLE)
    async def stafflink(self, interaction: discord.Interaction, member: discord.Member, ign: str) -> None:
        await interaction.response.defer()
        try:
            uuid = get_uuid(ign)
            manager.link_user(uuid, ign, member.id, member.name)
            embed = discord.Embed(
                colour=discord.Colour.dark_green(),
                description=(
                    f"__**Successfully Linked!**__\n"
                    f"**Discord:** {member.name}\n"
                    f"**IGN:** {ign}\n"
                    f"**UUID:** `{uuid}`"
                ),
            )
        except Exception as e:
            embed = discord.Embed(colour=discord.Colour.red(), description=str(e))
        await interaction.edit_original_response(embed=embed)


async def setup(client):
    await client.add_cog(StaffCommands(client))
