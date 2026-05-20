import random
import logging
import time
import discord
from lib.get_uuid import get_uuid
from db import manager


def roll_dye(username: str, bot, client) -> None:
    """Roll a random dye for a player and announce it if they get a new one."""
    try:
        uuid = get_uuid(username)
        dyes = manager.get_all_dyes_weighted()
        if not dyes:
            return

        dye_ids, weights = zip(*dyes)
        loot_id = random.choices(list(dye_ids), weights=weights, k=1)[0]

        if loot_id == "nothing":
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
        bot.chat(f"/gc DYE DROP: {username} found {dye_name} (1/{drop_rate:,})!")

        embed = discord.Embed(
            color=discord.Color.from_str(f"#{hex_color.lower()}"),
            title=username,
            description=f"Unlocked **{dye_name}** (1/{drop_rate:,})!",
        )
        client.bridge.send(embed=embed)
        client.dyes.send(embed=embed)
    except Exception as e:
        logging.error(e)
