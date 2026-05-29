import asyncio
import logging
from player import skyblock


async def guild_rank_change(guild_rank: str, bot, username: str = None, uuid: str = None,
                            send_msg: bool = True, ranks: dict = None,
                            known_level: float = None) -> str | None:
    """Promote or demote a guild member to match their Skyblock level against the rank table.

    Pass known_level to skip an extra API fetch when the level was already retrieved.
    Returns None if the bot is disconnected or an error occurs.
    """
    if ranks is None:
        return None

    if getattr(bot, "ended", True):
        logging.warning(f"guild_rank_change: bot is disconnected, skipping rank change for {username or uuid}")
        return None

    if guild_rank not in ranks:
        if send_msg:
            bot.chat(f"/gc {username}: No rank change possible!")
            return f"{username}: No rank change possible!"
        # Auto-rank from lowest when rank is unknown (e.g. fresh join with empty rank)
        guild_rank = list(ranks.keys())[0]

    if known_level is not None:
        skyblock_level = known_level
        display_name = username or str(uuid)
    else:
        player = skyblock.Player(uuid=uuid) if uuid else skyblock.Player(username=username)
        skyblock_level, _ = player.level.highest
        display_name = player.username

    try:
        required_rank = [rank for rank, level in ranks.items() if level < skyblock_level][-1]
        required_idx = list(ranks.keys()).index(required_rank)
        current_idx = list(ranks.keys()).index(guild_rank)
        delta = required_idx - current_idx

        if delta > 0:
            logging.info(f"Promoting {display_name}: {guild_rank} → {required_rank} ({delta} step(s))")
            for _ in range(delta):
                bot.chat(f"/g promote {display_name}")
                await asyncio.sleep(1.5)
            return f"Promoted {display_name} from {guild_rank} to {required_rank}"
        elif delta < 0:
            logging.info(f"Demoting {display_name}: {guild_rank} → {required_rank} ({abs(delta)} step(s))")
            for _ in range(abs(delta)):
                bot.chat(f"/g demote {display_name}")
                await asyncio.sleep(1.5)
            return f"Demoted {display_name} from {guild_rank} to {required_rank}"
        else:
            if send_msg:
                bot.chat(f"/gc {display_name}: No rank change required!")
            return f"{display_name}: No rank change required!"
    except Exception as e:
        logging.error(f"guild_rank_change error for {display_name}: {e}")
