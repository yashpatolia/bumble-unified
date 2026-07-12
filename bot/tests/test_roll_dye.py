"""Tests for utils/roll_dye.py — the weighted dye-drop roll and announcement."""
from unittest.mock import MagicMock, patch

from utils.roll_dye import roll_dye


def _client(guild_keys=("bk", "bu")):
    client = MagicMock()
    client.bridge = MagicMock()
    client.dyes = MagicMock()
    client.guilds_state = {key: MagicMock(bot=MagicMock()) for key in guild_keys}
    return client


def _bots(client):
    return [state.bot for state in client.guilds_state.values()]


@patch("utils.roll_dye.time.sleep")
@patch("utils.roll_dye.manager")
@patch("utils.roll_dye.get_uuid")
class TestRollDye:
    def test_rolling_above_pool_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        client = _client()

        with patch("utils.roll_dye.random.uniform", return_value=50.0):
            roll_dye("Player1", client)

        mock_manager.mark_dye_received.assert_not_called()
        for bot in _bots(client):
            bot.chat.assert_not_called()
        client.bridge.send.assert_not_called()
        client.dyes.send.assert_not_called()

    def test_no_dyes_configured_does_nothing(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = []
        client = _client()

        roll_dye("Player1", client)

        mock_manager.get_dye_received.assert_not_called()
        for bot in _bots(client):
            bot.chat.assert_not_called()

    def test_already_received_dye_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = True
        client = _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        mock_manager.mark_dye_received.assert_not_called()
        for bot in _bots(client):
            bot.chat.assert_not_called()
        client.bridge.send.assert_not_called()

    def test_unknown_dye_details_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = None
        client = _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        mock_manager.mark_dye_received.assert_not_called()
        for bot in _bots(client):
            bot.chat.assert_not_called()

    def test_new_dye_unlock_marks_received_and_announces(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Carmine Dye", 2.0e-05, "960018")
        client = _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        mock_manager.mark_dye_received.assert_called_once_with("uuid-1", "carmine_dye")
        client.bridge.send.assert_called_once()
        client.dyes.send.assert_called_once()

    def test_announces_to_every_connected_guild(self, mock_get_uuid, mock_manager, mock_sleep):
        """The in-game drop message must go out in every connected guild, not just one."""
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Carmine Dye", 2.0e-05, "960018")
        client = _client(guild_keys=("bk", "bu"))

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        for bot in _bots(client):
            bot.chat.assert_called_once()
            assert "Player1" in bot.chat.call_args[0][0]
            assert "Carmine Dye" in bot.chat.call_args[0][0]

    def test_skips_guilds_with_no_connected_bot(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Carmine Dye", 2.0e-05, "960018")
        client = _client()
        client.guilds_state["bu"].bot = None

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        client.guilds_state["bk"].bot.chat.assert_called_once()

    def test_drop_rate_matches_weight(self, mock_get_uuid, mock_manager, mock_sleep):
        """1/N in the announcement should be round(100 / weight)."""
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("livid_dye", 0.02)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Livid Dye", 0.02, "CEB7AA")
        client = _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", client)

        bot = next(iter(_bots(client)))
        assert "1/5,000" in bot.chat.call_args[0][0]

    def test_exception_is_swallowed(self, mock_get_uuid, mock_manager, mock_sleep):
        """roll_dye must never raise — errors are logged and swallowed."""
        mock_get_uuid.side_effect = RuntimeError("boom")
        client = _client()

        roll_dye("Player1", client)  # should not raise
