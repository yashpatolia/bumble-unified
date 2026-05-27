import asyncio
import logging
from lib import condense, guild_rank_change, fetch, get_uuid
from player import skyblock
from config import API_KEY, GuildConfig


async def bridge_commands(client, message: str, username: str, guild_rank: str,
                           chat_state: str, config: GuildConfig = None):
    """Route a dot-command from Minecraft or Discord to the appropriate handler."""
    try:
        parts = message.lower().split(" ")
        state = "/oc" if chat_state in ("Officer", "oc") else "/gc"
        webhook = client.officer if chat_state in ("Officer", "oc") else client.bridge

        command_map = {
            ".help":    lambda: _help(username),
            ".lvl":     lambda: _skyblock_level(username, parts),
            ".hlvl":    lambda: _highest_level(username, parts),
            ".nw":      lambda: _networth(username, parts, client),
            ".slayer":  lambda: _slayers(username, parts),
            ".slayers": lambda: _slayers(username, parts),
            ".cata":    lambda: _catacombs(username, parts),
            ".pb":      lambda: _catacombs_pb(username, parts),
            ".mp":      lambda: _magical_power(username, parts),
            ".bank":    lambda: _bank(username, parts),
            ".chim":    lambda: _chim(username, parts),
            ".ranks":   lambda: _ranks(client, state, username, webhook, config),
        }

        handler = command_map.get(parts[0])
        if handler is None:
            return

        try:
            result = await handler()
            if result is None:
                return
            name, response, raw_username = result

            for state_obj in client.guilds_state.values():
                if state_obj.bot:
                    state_obj.bot.chat(f"{state} {name}: {response}")
            webhook.send(response, username=name, avatar_url=f"https://mc-heads.net/avatar/{raw_username}")
        except Exception as e:
            logging.exception(e)
    except Exception as e:
        logging.exception(e)


async def _help(username: str):
    commands = ".lvl | .hlvl | .nw | .cata | .slayer | .pb (f/m)(1-7) | .mp | .bank | .chim <looting> <mf>"
    return username, commands, username


async def _skyblock_level(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return f"{player.username}{player.gamemode}", f"Skyblock Level - {player.level.current:.1f}", username


async def _highest_level(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    level, gamemode = player.level.highest
    return f"{player.username}{gamemode}", f"Highest Skyblock Level - {level:.1f}", username


async def _networth(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    nw = player.networth(client)
    return (
        f"{player.username}{player.gamemode}",
        f"Networth - {condense(nw.cosmetic_networth)} | Non-Cosmetic - {condense(nw.non_cosmetic_networth)}",
        username,
    )


async def _slayers(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return f"{player.username}{player.gamemode}", f"Slayer Levels - {player.slayers.levels}", username


async def _catacombs(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    cata = player.catacombs
    return (
        f"{player.username}{player.gamemode}",
        f"Cata Level - {cata.level} | Secrets - {cata.secrets:,} | S/R - {cata.spr}",
        username,
    )


async def _catacombs_pb(username: str, parts: list):
    if len(parts) < 2:
        return None
    username = parts[2] if len(parts) > 2 else username
    floor_type, floor = parts[1][0], parts[1][1]
    player = skyblock.Player(username=username)
    s_plus, s, comp, cata_type = player.catacombs.pb(floor_type, floor)
    return f"{player.username}", f"[{cata_type} {floor}] S+ {s_plus} | S {s} | Best {comp}", username


async def _magical_power(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    mp = player.magical_power
    return f"{player.username}{player.gamemode}", f"Total MP - {mp.total} | Highest MP - {mp.highest}", username


async def _bank(username: str, parts: list):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return (
        f"{player.username}{player.gamemode}",
        f"Bank - {condense(player.bank)} | Personal - {condense(player.personal_bank)} | Purse - {condense(player.purse)}",
        username,
    )


async def _chim(username: str, parts: list):
    if len(parts) < 3:
        return None
    looting, magic_find = int(parts[1]), int(parts[2])
    leg = 1 * (1 + looting * 0.15) * (1 + magic_find / 100)
    mythic = 1.25 * (1 + looting * 0.15) * (1 + magic_find / 100)
    return username, f"Chim Drop Rate: L{looting} & {magic_find}✯ [Leg: {leg:.2f}%] [Mythic: {mythic:.2f}%]", username


async def _ranks(client, state: str, username: str, webhook, config: GuildConfig):
    uuid = get_uuid(username)
    if config is None or uuid not in config.rank_update_users:
        return None

    msg = f"Now updating ranks for {config.display_name}... (May take a while!)"
    for state_obj in client.guilds_state.values():
        if state_obj.bot:
            state_obj.bot.chat(f"{state} {msg}")
    webhook.send(msg, username="Bumble")

    guild_data = await fetch(f"https://api.hypixel.net/v2/guild?name={config.display_name}&key={API_KEY}")
    mc_bot = client.guilds_state[config.key].bot

    for member in guild_data["guild"]["members"]:
        try:
            uuid = member["uuid"]
            rank = member["rank"]
            bot_rank = config.discord_rank_map.get(rank)
            if bot_rank is None:
                continue
            await guild_rank_change(bot_rank, mc_bot, uuid=uuid, send_msg=False, ranks=config.ranks)
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(e)

    return username, f"Finished updating ranks for {config.display_name}!", username
