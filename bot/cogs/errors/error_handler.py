import logging
import discord
from discord import app_commands
from discord.ext import commands


class ErrorHandling(commands.Cog):
    """Global slash-command error handler."""

    def __init__(self, client):
        self.client = client

    def cog_load(self):
        tree = self.client.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_tree_error

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, (app_commands.MissingRole, app_commands.MissingAnyRole)):
            message = "You don't have the required role to use this command."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"Command is on cooldown. Try again in {error.retry_after:.1f}s."
        else:
            logging.error(f"Unhandled slash command error: {error}")
            message = "An unexpected error occurred. Please try again."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(client):
    await client.add_cog(ErrorHandling(client))
