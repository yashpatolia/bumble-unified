import logging
from constants import DUNGEON_CLASS_DISPLAY, DUNGEON_CLASS_LETTERS, DUNGEON_CLASSES, DUNGEON_FLOOR_XP
from lib import condense
from lib.hypixel import fetch_mayor_multiplier
from player import skyblock
from player import PlayerNotFoundError, HypixelAPIError
from player.chimera import chim_drop_rates
from config import GuildConfig


async def bridge_commands(client, message: str, username: str, guild_rank: str,
                           chat_state: str, config: GuildConfig = None):
    """Route a dot-command from Minecraft or Discord to the appropriate handler."""
    try:
        parts = message.lower().split(" ")
        state = "/oc" if chat_state in ("Officer", "oc") else "/gc"
        webhook = client.officer if chat_state in ("Officer", "oc") else client.bridge

        command_map = {
            ".help":        _help,
            ".commands":    _help,
            ".lvl":         _skyblock_level,
            ".level":       _skyblock_level,
            ".sblvl":       _skyblock_level,
            ".hlvl":        _highest_level,
            ".hlevel":      _highest_level,
            ".nw":          _networth,
            ".networth":    _networth,
            ".slayer":      _slayers,
            ".slayers":     _slayers,
            ".slayerxp":    _slayer_xp,
            ".sxp":         _slayer_xp,
            ".cata":        _catacombs,
            ".catacombs":   _catacombs,
            ".rtca":        _runs_to_class_average,
            ".rtcaf":       _runs_to_class_average_skip,
            ".pb":          _catacombs_pb,
            ".pbs":         _catacombs_pb,
            ".mp":          _magical_power,
            ".magicalpower": _magical_power,
            ".bank":        _bank,
            ".chim":        _chim,
            ".petscore":    _petscore,
            ".pets":        _petscore,
        }

        handler = command_map.get(parts[0])
        if handler is None:
            return

        try:
            result = await handler(username, parts, client)
        except PlayerNotFoundError as e:
            target = str(e) or username
            result = (username, f"Couldn't find a Minecraft account named '{target}'", username)
        except HypixelAPIError as e:
            logging.exception(e)
            result = (username, "Hypixel API error, try that again in a moment", username)
        except Exception as e:
            logging.exception(e)
            result = (username, "Something went wrong running that command", username)

        if result is None:
            return
        name, response, raw_username = result

        try:
            for state_obj in client.guilds_state.values():
                if state_obj.bot:
                    state_obj.bot.chat(f"{state} {name}: {response}")
            webhook.send(response, username=name, avatar_url=f"https://mc-heads.net/avatar/{raw_username}")
        except Exception as e:
            logging.exception(e)
    except Exception as e:
        logging.exception(e)


async def _help(username: str, parts: list, client):
    commands = " | ".join([
        ".lvl", ".hlvl", ".nw", ".cata", ".rtca [floor]", ".rtcaf <1-4 letters>", ".slayer", ".slayerxp <type>", ".pb (f/m)(1-7)", ".mp", ".bank", ".chim <looting> <mf>", ".petscore"
    ])
    return username, commands, username


async def _skyblock_level(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return f"{player.username}{player.gamemode}", f"Skyblock Level - {player.level.current:.1f}", username


async def _highest_level(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    level, gamemode = player.level.highest
    return f"{player.username}{gamemode}", f"Highest Skyblock Level - {level:.1f}", username


async def _networth(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    nw = player.networth(client.skyhelper)
    return (
        f"{player.username}{player.gamemode}",
        f"Networth - {condense(nw.cosmetic_networth)} | Non-Cosmetic - {condense(nw.non_cosmetic_networth)}",
        username,
    )


async def _slayers(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return f"{player.username}{player.gamemode}", f"Slayer Levels - {player.slayers.levels}", username


async def _slayer_xp(username: str, parts: list, client):
    if len(parts) < 2:
        return username, "Usage: .slayerxp <type> [username]", username
    slayer_alias = parts[1]
    username = parts[2] if len(parts) > 2 else username
    player = skyblock.Player(username=username)
    result = player.slayers.xp_for(slayer_alias)
    if result is None:
        return f"{username}", f"Unknown slayer '{slayer_alias}'", username
    display_name, xp = result
    return f"{player.username}{player.gamemode}", f"{display_name} XP - {xp:,}", username


async def _catacombs(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    cata = player.catacombs
    return (
        f"{player.username}{player.gamemode}",
        f"Cata Level - {cata.level} | Secrets - {cata.secrets:,} | S/R - {cata.spr}",
        username,
    )


_RTCA_USAGE = "Usage: .rtca [username] [floor f1-f7/m1-m7], e.g. .rtca steve m6"


async def _runs_to_class_average(username: str, parts: list, client):
    args = [a for a in parts[1:] if a]
    # A leading argument that is a floor belongs to the sender, so .rtca m6 still means "me".
    if args and args[0] not in DUNGEON_FLOOR_XP:
        username = args.pop(0)

    floor = "m7"
    for arg in args:
        if arg not in DUNGEON_FLOOR_XP:
            return username, _RTCA_USAGE, username
        floor = arg

    player = skyblock.Player(username=username)
    mayor_multiplier = await fetch_mayor_multiplier()
    total, per_class = player.class_average.runs_to_target(
        DUNGEON_FLOOR_XP[floor], mayor_multiplier=mayor_multiplier
    )

    name = f"{player.username}{player.gamemode}"
    if total == 0:
        return name, "Already CA50", username

    floor_name = floor.title() if floor == "entrance" else floor.upper()
    # Classes needing no dedicated runs reach 50 on passive XP alone - listing them as 0 is noise.
    breakdown = " | ".join(
        f"{DUNGEON_CLASS_DISPLAY[c]} {per_class[c]:,}" for c in DUNGEON_CLASSES if per_class[c]
    )
    return name, f"{total:,} {floor_name} runs to CA50 | {breakdown}", username


_RTCAF_USAGE = ("Usage: .rtcaf [username] <letters> [floor] - skip 1-4 classes, "
                "a=archer b=berserk h=healer m=mage t=tank, e.g. .rtcaf a h m6")


async def _runs_to_class_average_skip(username: str, parts: list, client):
    args = [a for a in parts[1:] if a]
    floor = "m7"
    skip_letters = []
    for arg in args:
        if arg in DUNGEON_FLOOR_XP:
            floor = arg
        elif arg in DUNGEON_CLASS_LETTERS:
            skip_letters.append(arg)
        else:
            username = arg

    skip_letters = set(skip_letters)
    if not 1 <= len(skip_letters) <= 4:
        return username, _RTCAF_USAGE, username

    skip_classes = {DUNGEON_CLASS_LETTERS[letter] for letter in skip_letters}
    active_classes = tuple(c for c in DUNGEON_CLASSES if c not in skip_classes)

    player = skyblock.Player(username=username)
    mayor_multiplier = await fetch_mayor_multiplier()
    class_average = player.class_average
    total, _ = class_average.runs_to_target(
        DUNGEON_FLOOR_XP[floor], mayor_multiplier=mayor_multiplier, playable=active_classes
    )

    name = f"{player.username}{player.gamemode}"
    if total == 0:
        return name, "Already CA50", username

    # The minimum dedicated plays each active class needs - once met, further runs can go to
    # any active class (passive share depends only on total runs, not who else was played).
    needed = class_average.minimum_runs_needed(
        DUNGEON_FLOOR_XP[floor], total, mayor_multiplier=mayor_multiplier, playable=active_classes
    )
    slack = total - sum(needed.values())

    floor_name = floor.title() if floor == "entrance" else floor.upper()
    skipped = "+".join(DUNGEON_CLASS_DISPLAY[c] for c in DUNGEON_CLASSES if c in skip_classes)
    dedicated = " | ".join(
        f"{DUNGEON_CLASS_DISPLAY[c]} {needed[c]:,}" for c in active_classes if needed[c]
    )
    any_active = "/".join(DUNGEON_CLASS_DISPLAY[c] for c in active_classes)
    any_phrase = f"play {any_active}" if len(active_classes) == 1 else f"any of {any_active}"
    if dedicated and slack > 0:
        breakdown = f"{dedicated} | then {slack:,} runs, any class"
    elif dedicated:
        breakdown = dedicated
    else:
        breakdown = f"{any_phrase} the whole way"

    return name, f"{total:,} {floor_name} runs to CA50 (skip {skipped}) | {breakdown}", username


async def _catacombs_pb(username: str, parts: list, client):
    if len(parts) < 2 or len(parts[1]) != 2 or parts[1][0] not in ("f", "m"):
        return username, "Usage: .pb (f/m)(1-7) [username], e.g. .pb f7", username
    username = parts[2] if len(parts) > 2 else username
    floor_type, floor = parts[1][0], parts[1][1]
    player = skyblock.Player(username=username)
    s_plus, s, comp, cata_type = player.catacombs.pb(floor_type, floor)
    return f"{player.username}", f"[{cata_type} {floor}] S+ {s_plus} | S {s} | Best {comp}", username


async def _magical_power(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    mp = player.magical_power
    return f"{player.username}{player.gamemode}", f"Total MP - {mp.total} | Highest MP - {mp.highest}", username


async def _bank(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return (
        f"{player.username}{player.gamemode}",
        f"Bank - {condense(player.bank)} | Personal - {condense(player.personal_bank)} | Purse - {condense(player.purse)}",
        username,
    )


async def _chim(username: str, parts: list, client):
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return username, "Usage: .chim <looting level> <magic find>", username
    looting, magic_find = int(parts[1]), int(parts[2])
    rates = chim_drop_rates(looting, magic_find)
    return username, f"Chim Drop Rate: L{looting} & {magic_find}✯ [Leg: {rates['legendary']:.2f}%] [Mythic: {rates['mythic']:.2f}%]", username


async def _petscore(username: str, parts: list, client):
    username = parts[1] if len(parts) > 1 else username
    player = skyblock.Player(username=username)
    return f"{player.username}{player.gamemode}", f"Pet Score - {player.pet_score}", username


