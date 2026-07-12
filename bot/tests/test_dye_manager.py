"""Tests for the dye-related DatabaseManager methods (db/manager.py).

psycopg2 is stubbed in conftest.py, so DatabaseManager talks to MagicMock
connections/cursors — these tests assert the SQL shape and params, not
against a real database.
"""
from unittest.mock import MagicMock

from db.manager import DatabaseManager


def _manager_with_mock_cursor():
    """Build a DatabaseManager whose _cursor() context manager yields a controllable mock cursor."""
    mgr = DatabaseManager(dsn="postgresql://unused")
    mock_cursor = MagicMock()
    mgr._cursor = MagicMock()
    mgr._cursor.return_value.__enter__.return_value = mock_cursor
    return mgr, mock_cursor


class TestMarkDyeReceived:
    def test_upserts_instead_of_bare_update(self):
        """Regression test: a bare UPDATE silently no-ops on a first-time unlock
        because no row exists yet in users_dyes. Must be an INSERT ... ON CONFLICT."""
        mgr, cur = _manager_with_mock_cursor()

        mgr.mark_dye_received("uuid-1", "carmine_dye")

        cur.execute.assert_called_once()
        query, params = cur.execute.call_args[0]
        assert "INSERT INTO users_dyes" in query
        assert "ON CONFLICT" in query
        assert "DO UPDATE SET received = TRUE" in query
        assert params == ("uuid-1", "carmine_dye")

    def test_conflict_target_is_uuid_and_dye_id(self):
        mgr, cur = _manager_with_mock_cursor()

        mgr.mark_dye_received("uuid-2", "livid_dye")

        query = cur.execute.call_args[0][0]
        assert "(uuid, dye_id)" in query


class TestResetAllDyeRolls:
    def test_deletes_all_rows_and_returns_count(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.rowcount = 42

        result = mgr.reset_all_dye_rolls()

        cur.execute.assert_called_once_with("DELETE FROM users_dyes")
        assert result == 42
