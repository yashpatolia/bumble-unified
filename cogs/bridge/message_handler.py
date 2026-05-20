import logging
import re
import discord
from discord.ext import commands
from javascript import On
from config import GuildConfig
from player import skyblock


class GuildMessageHandler(commands.Cog):
    """Parses Minecraft system messages for one guild and forwards relevant events to Discord."""

    def __init__(self, client, config: GuildConfig):
        self.__cog_name__ = f"{config.key}_message_handler"
        super().__init__()
        self.client = client
        self.config = config
        state = self.client.guilds_state[config.key]

        @On(state.bot, "messagestr")
        def on_messagestr(this, message, *args) -> None:
            if not message:
                return

            logging.debug(f"[MC/{config.short_name}] {message}")

            # Accumulate /guild list and /guild online output
            if "Online Members:" in message and state.save_guild_list:
                state.guild_list.append(message)
                state.save_guild_list = False
            if state.save_guild_list:
                state.guild_list.append(message)
            if f"Guild Name: {config.guild_name}" in message:
                state.save_guild_list = True

            # Ignore regular guild/officer chat (handled by bridge.py)
            if message.split(" ")[0] in ("Guild", "Officer"):
                return

            logs = state.logs

            if message.lower().startswith("you cannot say the same message twice!"):
                embed = discord.Embed(colour=discord.Colour.dark_red(), description="Duplicate message!")
                self.client.bridge.send(embed=embed)

            if message.lower().endswith("not found."):
                embed = discord.Embed(colour=discord.Colour.red(), description=message)
                self.client.bridge.send(embed=embed)
                logs.send(embed=embed)

            if "was promoted from" in message.lower() or "was demoted from" in message.lower():
                embed = discord.Embed(colour=discord.Colour.dark_teal(), description=message)
                self.client.bridge.send(embed=embed)
                logs.send(embed=embed)

            # Invite result messages
            invite_errors = [
                "is already in another guild!",
                "cannot invite this player to your guild!",
                "can't find a player by the name of",
            ]
            for phrase in invite_errors:
                if phrase in message.lower():
                    state.guild_invite = message
                    embed = discord.Embed(colour=discord.Colour.dark_red(), description=message)
                    logs.send(embed=embed)
                    break

            invite_ok = [
                "was invited to the",
                "to your guild",
                "you sent an offline invite",
            ]
            if any(p in message.lower() for p in invite_ok):
                state.guild_invite = message
                embed = discord.Embed(colour=discord.Colour.orange(), description=message)
                logs.send(embed=embed)

            if "joined the guild!" in message.lower():
                embed = discord.Embed(colour=discord.Colour.dark_green(), description=f"[{config.short_name}] {message}")
                self.client.officer.send(embed=embed)
                self.client.bridge.send(embed=embed)
                logs.send(embed=embed)

            if "left the guild!" in message.lower():
                embed = discord.Embed(colour=discord.Colour.red(), description=f"[{config.short_name}] {message}")
                self.client.bridge.send(embed=embed)
                self.client.officer.send(embed=embed)
                logs.send(embed=embed)

            if "has muted" in message.lower() and "for" in message.lower():
                embed = discord.Embed(colour=discord.Colour.dark_purple(), description=message)
                self.client.bridge.send(embed=embed)
                logs.send(embed=embed)

            if "has unmuted" in message.lower():
                embed = discord.Embed(colour=discord.Colour.dark_magenta(), description=message)
                self.client.bridge.send(embed=embed)
                logs.send(embed=embed)

            if "was kicked from the guild" in message.lower():
                embed = discord.Embed(colour=discord.Colour.dark_red(), description=f"[{config.short_name}] {message}")
                self.client.bridge.send(embed=embed)
                self.client.officer.send(embed=embed)
                logs.send(embed=embed)

            if "has requested to join the guild!" in message.lower():
                match = re.search(r"(?:\[(?P<rank>\w+)\]\s+)?(?P<player>\w+)\s+has requested to join the Guild!", message)
                if match:
                    username = match.group("player")
                    try:
                        player = skyblock.Player(username=username)
                        skyblock_level, gamemode = player.level.highest
                        embed = discord.Embed(
                            colour=discord.Colour.dark_blue(),
                            description=f"{gamemode}`{player.username}` requested to join [{config.short_name}]! [Level: {skyblock_level:.1f}]",
                        )
                        self.client.officer.send(embed=embed)
                        logs.send(embed=embed)
                    except Exception as e:
                        logging.error(e)


async def setup(client):
    for config in client.guild_configs.values():
        await client.add_cog(GuildMessageHandler(client, config))
