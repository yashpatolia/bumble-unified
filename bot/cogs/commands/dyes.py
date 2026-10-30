import discord
from discord.ext import commands
from discord import app_commands
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

        # Roles and emojis are set per dye on the panel's Config page (dyes table).
        dye_roles = manager.get_dye_roles()
        new_role = interaction.guild.get_role(dye_roles[dye]) if dye in dye_roles else None
        if new_role is None:
            await interaction.edit_original_response(
                embed=discord.Embed(colour=discord.Colour.dark_red(), description=f"{dye_name} has no Discord role set up yet.")
            )
            return

        # Swap dye roles
        for role_id in dye_roles.values():
            role = interaction.guild.get_role(role_id)
            if role in interaction.user.roles and role != new_role:
                await interaction.user.remove_roles(role)
        await interaction.user.add_roles(new_role)

        emoji_id = manager.get_dye_emoji(dye)
        emoji = f"<:{dye}:{emoji_id}> " if emoji_id else ""
        embed = discord.Embed(
            color=discord.Color.from_str(f"#{hex_color.lower()}"),
            description=f"**Selected:** {emoji}{dye_name}",
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
