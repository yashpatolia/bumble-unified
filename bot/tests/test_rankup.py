"""Tests for guild_rank_change (lib/rankup.py).

All tests pass known_level so no Hypixel API calls are made.
asyncio.sleep is patched to run instantly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lib.rankup import guild_rank_change

# Rank table matching the BK guild structure (level threshold to *enter* rank)
RANKS = {
    "Baby":  0,
    "Tot":   50,
    "Sweat": 150,
    "Pro":   300,
}


@pytest.fixture
def bot():
    b = MagicMock()
    b.chat = MagicMock()
    return b


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


# ── Basic guards ───────────────────────────────────────────────────────────

async def test_returns_none_when_no_ranks(bot):
    result = await guild_rank_change("Baby", bot, username="X", ranks=None, known_level=80.0)
    assert result is None
    bot.chat.assert_not_called()


# ── Promotions ─────────────────────────────────────────────────────────────

async def test_promote_one_step(bot):
    result = await guild_rank_change(
        "Baby", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=80.0
    )
    assert result == "Promoted Player1 from Baby to Tot"
    bot.chat.assert_called_once_with("/g promote Player1")

async def test_promote_two_steps(bot):
    result = await guild_rank_change(
        "Baby", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=200.0
    )
    assert result == "Promoted Player1 from Baby to Sweat"
    assert bot.chat.call_count == 2
    bot.chat.assert_any_call("/g promote Player1")

async def test_promote_three_steps_to_max(bot):
    result = await guild_rank_change(
        "Baby", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=350.0
    )
    assert result == "Promoted Player1 from Baby to Pro"
    assert bot.chat.call_count == 3


# ── Demotions ──────────────────────────────────────────────────────────────

async def test_demote_one_step(bot):
    result = await guild_rank_change(
        "Sweat", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=80.0
    )
    assert result == "Demoted Player1 from Sweat to Tot"
    bot.chat.assert_called_once_with("/g demote Player1")

async def test_demote_two_steps(bot):
    result = await guild_rank_change(
        "Pro", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=30.0
    )
    assert result == "Demoted Player1 from Pro to Baby"
    assert bot.chat.call_count == 3


# ── No change ──────────────────────────────────────────────────────────────

async def test_no_change_needed(bot):
    result = await guild_rank_change(
        "Tot", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=80.0
    )
    assert result == "Player1: No rank change required!"
    bot.chat.assert_not_called()

async def test_no_change_at_max_rank(bot):
    result = await guild_rank_change(
        "Pro", bot, username="Player1", ranks=RANKS, send_msg=False, known_level=350.0
    )
    assert result == "Player1: No rank change required!"
    bot.chat.assert_not_called()


# ── Unknown / empty rank (new joins) ──────────────────────────────────────

async def test_unknown_rank_falls_back_to_lowest(bot):
    """New joins have rank='' — should auto-start from Baby."""
    result = await guild_rank_change(
        "", bot, username="NewPlayer", ranks=RANKS, send_msg=False, known_level=80.0
    )
    assert result == "Promoted NewPlayer from Baby to Tot"

async def test_unknown_rank_with_send_msg_returns_message(bot):
    """With send_msg=True, unknown rank sends an in-game chat message."""
    result = await guild_rank_change(
        "GuildMaster", bot, username="GM", ranks=RANKS, send_msg=True, known_level=80.0
    )
    assert result == "GM: No rank change possible!"
    bot.chat.assert_called_once_with("/gc GM: No rank change possible!")


# ── known_level skips extra API fetch ─────────────────────────────────────

async def test_known_level_does_not_call_skyblock(bot):
    """When known_level is provided, skyblock.Player must never be instantiated."""
    with patch("lib.rankup.skyblock") as mock_skyblock:
        await guild_rank_change(
            "Baby", bot, username="P", ranks=RANKS, send_msg=False, known_level=80.0
        )
    mock_skyblock.Player.assert_not_called()


# ── display_name falls back to uuid string if username is None ─────────────

async def test_display_name_uses_uuid_when_no_username(bot):
    result = await guild_rank_change(
        "Baby", bot, uuid="abc-123", ranks=RANKS, send_msg=False, known_level=80.0
    )
    assert "abc-123" in result
    bot.chat.assert_called_once_with("/g promote abc-123")
