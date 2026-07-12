import random
import logging
import time
import discord
from lib.get_uuid import get_uuid
from db import manager


def roll_dye(username: str, client) -> None:
    """Roll a random dye for a player and announce it if they get a new one."""
    try:
        uuid = get_uuid(username)
        dyes = manager.get_all_dyes_weighted()
        if not dyes:
            return

        # Each dye's weight is its percent chance out of a 100-point pool;
        # whatever isn't covered by real dyes is an implicit "no drop".
        roll = random.uniform(0, 100)
        cumulative = 0.0
        loot_id = None
        for dye_id, weight in dyes:
            cumulative += weight
            if roll <= cumulative:
                loot_id = dye_id
                break

        if loot_id is None:
            return

        received = manager.get_dye_received(uuid, loot_id)
        if received:
            return

        dye_info = manager.get_dye_details(loot_id)
        if not dye_info:
            return

        dye_name, weight, hex_color = dye_info
        manager.mark_dye_received(uuid, loot_id)

        drop_rate = round(100 / weight)
        logging.warning(f"{username} unlocked {dye_name}! (1/{drop_rate:,})")

        time.sleep(0.5)
        message = f"/gc DYE DROP: {username} found {dye_name} (1/{drop_rate:,})!"
        for state in client.guilds_state.values():
            if state.bot:
                state.bot.chat(message)

        embed = discord.Embed(
            color=discord.Color.from_str(f"#{hex_color.lower()}"),
            title=username,
            description=f"Unlocked **{dye_name}** (1/{drop_rate:,})!",
        )
        client.bridge.send(embed=embed)
        client.dyes.send(embed=embed)
    except Exception as e:
        logging.error(e)
