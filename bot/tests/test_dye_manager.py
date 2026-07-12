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


class TestGetAllDyes:
    def test_returns_full_rows_ordered_by_weight(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.fetchall.return_value = [("dark_purple_dye", "Dark Purple Dye", 0.25, "301934")]

        result = mgr.get_all_dyes()

        query = cur.execute.call_args[0][0]
        assert "SELECT dye_id, dye_name, weight, hex FROM dyes" in query
        assert "ORDER BY weight DESC" in query
        assert result == [("dark_purple_dye", "Dark Purple Dye", 0.25, "301934")]


class TestGetUserByUuid:
    def test_queries_by_uuid(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.fetchone.return_value = ("Player1", 123, "Player1#0", "https://example.com/a.png")

        result = mgr.get_user_by_uuid("uuid-1")

        query, params = cur.execute.call_args[0]
        assert "FROM users WHERE uuid = %s" in query
        assert params == ("uuid-1",)
        assert result == ("Player1", 123, "Player1#0", "https://example.com/a.png")

    def test_returns_none_when_not_found(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.fetchone.return_value = None

        assert mgr.get_user_by_uuid("missing-uuid") is None


class TestSearchUsersWithDyeCounts:
    def test_query_shape_and_params(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.fetchall.return_value = []

        mgr.search_users_with_dye_counts("play", limit=10)

        query, params = cur.execute.call_args[0]
        assert "LEFT JOIN users_dyes" in query
        assert "WHERE u.ign ILIKE %s" in query
        assert "GROUP BY u.uuid" in query
        assert params == ("%play%", 10)

    def test_returns_rows(self):
        mgr, cur = _manager_with_mock_cursor()
        cur.fetchall.return_value = [("uuid-1", "Player1", 123, "Player1#0", None, 3)]

        result = mgr.search_users_with_dye_counts("Player1")

        assert result == [("uuid-1", "Player1", 123, "Player1#0", None, 3)]
