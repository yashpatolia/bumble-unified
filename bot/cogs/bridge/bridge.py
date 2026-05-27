import logging
import re
import discord
import emoji
from asyncio import run_coroutine_threadsafe
from discord.ext import commands
from javascript import On
from config import GuildConfig
from db import manager
from utils.command_handler import bridge_commands


class GuildBridge(commands.Cog):
    """
    Handles message bridging for one Minecraft guild.

    Minecraft → Discord: forwards guild/officer chat to the shared bridge webhook.
    Discord → Minecraft: only active when config.bridge_channel_id is set (i.e. BK).
                         Messages from that Discord channel are sent to ALL guild bots.
    """

    def __init__(self, client, config: GuildConfig):
        self.__cog_name__ = f"{config.key}_bridge"
        super().__init__()
        self.client = client
        self.config = config
        state = self.client.guilds_state[config.key]

        @On(state.bot, "chat")
        def handle_minecraft_message(this, username, message, *args):
            if username not in ("Guild", "Officer"):
                return

            try:
                # Online/offline join-leave system messages (no colon, not bot itself)
                if (
                    message.split(" ")[-1] in ("joined.", "left.")
                    and ":" not in message.lower()
                    and config.mc_username.lower() not in message.lower()
                ):
                    embed = discord.Embed(description=message)
                    embed.colour = discord.Color.green() if message.endswith("joined.") else discord.Color.red()
                    self.client.bridge.send(embed=embed)
                    return

                logging.debug(f"[MC/{config.short_name}] {username}: {message}")
                chat_type = username  # "Guild" or "Officer"

                match = re.search(
                    r"^(?:\[(?P<rank>.+?)\])?\s?(?P<player>.+?)\s?(?:\[(?P<guild_rank>.+?)\])?: (?P<message>.*)$",
                    message,
                )
                if not match:
                    return

                msg_text = re.sub("@", "", match.group("message")).strip()
                sender = match.group("player")
                guild_rank = match.group("guild_rank")

                all_bot_usernames = {cfg.mc_username for cfg in self.client.guild_configs.values()}
                if sender in all_bot_usernames:
                    return

                webhook = self.client.officer if chat_type == "Officer" else self.client.bridge
                webhook.send(
                    msg_text,
                    username=f"[{config.short_name}] {sender}",
                    avatar_url=f"https://mc-heads.net/avatar/{sender}",
                )
                self.client.message_logs.send(
                    f"{sender} | {msg_text}",
                    username=sender,
                    avatar_url=f"https://mc-heads.net/avatar/{sender}",
                )

                # Relay to all other guild bots
                relay_state = "/oc" if chat_type == "Officer" else "/gc"
                for key, other_state in self.client.guilds_state.items():
                    if key != config.key and other_state.bot:
                        other_state.bot.chat(f"{relay_state} [{config.short_name}] {sender}: {msg_text}")

                if msg_text.startswith("."):
                    run_coroutine_threadsafe(
                        bridge_commands(self.client, msg_text, sender, guild_rank, chat_type, config=config),
                        self.client.loop,
                    )
            except Exception as e:
                logging.exception(e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Only the guild with a configured bridge_channel_id handles Discord → Minecraft
        if self.config.bridge_channel_id is None:
            return
        if (
            not (message.content or message.attachments)
            or message.author.bot
            or message.channel.id not in (self.config.bridge_channel_id, self.config.officer_channel_id)
        ):
            return

        logging.debug(f"[Discord/{message.channel.name}] {message.author.display_name}: {message.content}")

        chat_state = "oc" if message.channel.id == self.config.officer_channel_id else "gc"
        webhook = self.client.officer if chat_state == "oc" else self.client.bridge

        content = emoji.demojize(message.clean_content)
        content = re.sub(r"<[^:]*(:[^:]+:)\d+>", r"\1", content)
        command_check = content

        # Resolve IGN for author and (if reply) the replied-to user
        ign = manager.get_ign(message.author.id) or message.author.display_name
        if message.type == discord.MessageType.reply:
            reply_msg = await message.channel.fetch_message(message.reference.message_id)
            reply_ign = manager.get_ign(reply_msg.author.id) or reply_msg.author.display_name
            content = f"{ign} ➜ {reply_ign}: {content}"
        else:
            content = f"{ign}: {content}"

        if message.attachments:
            content += f" [{len(message.attachments)} img(s)]"

        if len(content) > 250:
            embed = discord.Embed(description="Message too long to send!", colour=discord.Color.dark_red())
            webhook.send(embed=embed)
            return

        # Send to all guild bots
        for state in self.client.guilds_state.values():
            if state.bot:
                state.bot.chat(f"/{chat_state} {content}")

        if command_check.startswith("."):
            run_coroutine_threadsafe(
                bridge_commands(self.client, command_check, message.author.display_name, "None", chat_state, config=self.config),
                self.client.loop,
            )


async def setup(client):
    for config in client.guild_configs.values():
        await client.add_cog(GuildBridge(client, config))
