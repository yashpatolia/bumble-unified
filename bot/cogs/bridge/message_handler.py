import asyncio
import logging
import re
import aiohttp
import discord
from discord.ext import commands
from javascript import On
from config import GuildConfig
from db import manager
from lib.get_uuid import get_uuid
from lib.hypixel import fetch_member_stats
from lib.rankup import guild_rank_change
from player import skyblock


async def _auto_fetch_and_rank(client, config: GuildConfig, ign: str) -> None:
    """Fetch stats for a newly joined member and auto-rank them."""
    await asyncio.sleep(5)  # brief settle time
    try:
        uuid = await asyncio.to_thread(get_uuid, ign)
        if uuid:
            manager.update_guild_member_uuid(config.key, ign, uuid)
        else:
            logging.warning(f"[{config.short_name}] Auto-fetch: could not resolve UUID for {ign}")
            return

        async with aiohttp.ClientSession() as session:
            stats = await fetch_member_stats(session, uuid)

        manager.update_guild_member_stats(config.key, ign, stats["skyblock_level"], stats["last_login"])

        level = stats["skyblock_level"]
        if level is None:
            return

        starting_rank = list(config.ranks.keys())[0]
        state = client.guilds_state[config.key]
        result = await guild_rank_change(
            starting_rank, state.bot, username=ign, uuid=uuid,
            ranks=config.ranks, send_msg=False, known_level=level,
        )
        if result:
            logging.info(f"[{config.short_name}] Auto-rank {ign}: {result}")
            embed = discord.Embed(
                colour=discord.Colour.teal(),
                description=f"[{config.short_name}] Auto-ranked **{ign}** (Level {level:.1f}): {result}",
            )
            state.logs.send(embed=embed)
    except Exception as e:
        logging.error(f"[{config.short_name}] Auto-fetch failed for {ign}: {e}")


class GuildMessageHandler(commands.Cog):
    """Parses Minecraft system messages for one guild and forwards relevant events to Discord."""

    def __init__(self, client, config: GuildConfig):
        self.__cog_name__ = f"{config.key}_message_handler"
        super().__init__()
        self.client = client
        self.config = config
        self._loop = asyncio.get_event_loop()
        state = self.client.guilds_state[config.key]

        @On(state.bot, "messagestr")
        def on_messagestr(this, message, *args) -> None:
            if not message:
                return

            logging.debug(f"[MC/{config.short_name}] {message}")

            # Accumulate /guild list output
            if "Online Members:" in message and state.save_guild_list:
                state.guild_list.append(message)
                state.save_guild_list = False
            if state.save_guild_list:
                state.guild_list.append(message)
            if f"Guild Name: {config.guild_name}" in message:
                state.save_guild_list = True

            # Accumulate /guild online output (flag set externally by IPC)
            if state.save_guild_online:
                state.guild_online.append(message)

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
                m = re.search(r"(?:\[[\w+]+\]\s+)?(\w+)\s+was (?:promoted|demoted) from .+? to ([A-Za-z ]+?)(?:[!.]|$)", message, re.IGNORECASE)
                if m:
                    manager.upsert_guild_member(config.key, m.group(1), m.group(2))

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
                m = re.search(r"(?:\[[\w+]+\]\s+)?(\w+)\s+joined the guild", message, re.IGNORECASE)
                if m:
                    ign = m.group(1)
                    manager.upsert_guild_member(config.key, ign, '')
                    asyncio.run_coroutine_threadsafe(
                        _auto_fetch_and_rank(self.client, config, ign),
                        self._loop,
                    )

            if "left the guild!" in message.lower():
                embed = discord.Embed(colour=discord.Colour.red(), description=f"[{config.short_name}] {message}")
                self.client.bridge.send(embed=embed)
                self.client.officer.send(embed=embed)
                logs.send(embed=embed)
                m = re.search(r"(?:\[[\w+]+\]\s+)?(\w+)\s+left the guild", message, re.IGNORECASE)
                if m:
                    manager.remove_guild_member(config.key, m.group(1))

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
                m = re.search(r"(?:\[[\w+]+\]\s+)?(\w+)\s+was kicked from the guild", message, re.IGNORECASE)
                if m:
                    manager.remove_guild_member(config.key, m.group(1))

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
