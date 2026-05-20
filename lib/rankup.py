import asyncio
import logging
from player import skyblock


async def guild_rank_change(guild_rank: str, bot, username: str = None, uuid: str = None,
                            send_msg: bool = True, ranks: dict = None) -> str | None:
    """Promote or demote a guild member to match their Skyblock level against the rank table."""
    if ranks is None:
        return None

    if guild_rank not in ranks and send_msg:
        bot.chat(f"/gc {username}: No rank change possible!")
        return f"{username}: No rank change possible!"

    player = skyblock.Player(uuid=uuid) if uuid else skyblock.Player(username=username)
    skyblock_level, _ = player.level.highest

    try:
        required_rank = [rank for rank, level in ranks.items() if level < skyblock_level][-1]
        required_idx = list(ranks.keys()).index(required_rank)
        current_idx = list(ranks.keys()).index(guild_rank)
        delta = required_idx - current_idx

        logging.info(f"{player.username}: {guild_rank} → {required_rank}")

        if delta > 0:
            for _ in range(delta):
                bot.chat(f"/g promote {player.username}")
                await asyncio.sleep(1)
            return f"Promoted {player.username} from {guild_rank} to {required_rank}"
        elif delta < 0:
            for _ in range(abs(delta)):
                bot.chat(f"/g demote {player.username}")
                await asyncio.sleep(1)
            return f"Demoted {player.username} from {guild_rank} to {required_rank}"
        else:
            if send_msg:
                bot.chat(f"/gc {player.username}: No rank change required!")
            return f"{player.username}: No rank change required!"
    except Exception as e:
        logging.error(e)
