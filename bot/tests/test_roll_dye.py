"""Tests for utils/roll_dye.py — the weighted dye-drop roll and announcement."""
from unittest.mock import MagicMock, patch

from utils.roll_dye import roll_dye


def _client():
    client = MagicMock()
    client.bridge = MagicMock()
    client.dyes = MagicMock()
    return client


def _bot():
    return MagicMock()


@patch("utils.roll_dye.time.sleep")
@patch("utils.roll_dye.manager")
@patch("utils.roll_dye.get_uuid")
class TestRollDye:
    def test_rolling_above_pool_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        bot, client = _bot(), _client()

        with patch("utils.roll_dye.random.uniform", return_value=50.0):
            roll_dye("Player1", bot, client)

        mock_manager.mark_dye_received.assert_not_called()
        bot.chat.assert_not_called()
        client.bridge.send.assert_not_called()
        client.dyes.send.assert_not_called()

    def test_no_dyes_configured_does_nothing(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = []
        bot, client = _bot(), _client()

        roll_dye("Player1", bot, client)

        mock_manager.get_dye_received.assert_not_called()
        bot.chat.assert_not_called()

    def test_already_received_dye_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = True
        bot, client = _bot(), _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", bot, client)

        mock_manager.mark_dye_received.assert_not_called()
        bot.chat.assert_not_called()
        client.bridge.send.assert_not_called()

    def test_unknown_dye_details_sends_no_announcement(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = None
        bot, client = _bot(), _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", bot, client)

        mock_manager.mark_dye_received.assert_not_called()
        bot.chat.assert_not_called()

    def test_new_dye_unlock_marks_received_and_announces(self, mock_get_uuid, mock_manager, mock_sleep):
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("carmine_dye", 2.0e-05)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Carmine Dye", 2.0e-05, "960018")
        bot, client = _bot(), _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", bot, client)

        mock_manager.mark_dye_received.assert_called_once_with("uuid-1", "carmine_dye")
        bot.chat.assert_called_once()
        assert "Player1" in bot.chat.call_args[0][0]
        assert "Carmine Dye" in bot.chat.call_args[0][0]
        client.bridge.send.assert_called_once()
        client.dyes.send.assert_called_once()

    def test_drop_rate_matches_weight(self, mock_get_uuid, mock_manager, mock_sleep):
        """1/N in the announcement should be round(100 / weight)."""
        mock_get_uuid.return_value = "uuid-1"
        mock_manager.get_all_dyes_weighted.return_value = [("livid_dye", 0.02)]
        mock_manager.get_dye_received.return_value = False
        mock_manager.get_dye_details.return_value = ("Livid Dye", 0.02, "CEB7AA")
        bot, client = _bot(), _client()

        with patch("utils.roll_dye.random.uniform", return_value=0.0):
            roll_dye("Player1", bot, client)

        assert "1/5,000" in bot.chat.call_args[0][0]

    def test_exception_is_swallowed(self, mock_get_uuid, mock_manager, mock_sleep):
        """roll_dye must never raise — errors are logged and swallowed."""
        mock_get_uuid.side_effect = RuntimeError("boom")
        bot, client = _bot(), _client()

        roll_dye("Player1", bot, client)  # should not raise
