import datetime as _dt

from db.base import BaseQueries


class ApiUsageQueries(BaseQueries):
    """Hypixel API call logging (`api_calls`), backing the panel's usage view."""

    def record_api_call(self, endpoint: str, success: bool = True) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO api_calls (called_at, endpoint, success) VALUES (%s, %s, %s)",
                (_dt.datetime.now(_dt.timezone.utc), endpoint, success),
            )

    def get_api_call_counts(self) -> dict:
        """Returns API call counts for several rolling windows."""
        now = _dt.datetime.now(_dt.timezone.utc)
        windows = {
            "last_minute": now - _dt.timedelta(minutes=1),
            "last_5min": now - _dt.timedelta(minutes=5),
            "last_hour": now - _dt.timedelta(hours=1),
            "today": now - _dt.timedelta(hours=24),
        }
        result = {}
        with self._cursor() as cur:
            for key, since in windows.items():
                cur.execute("SELECT COUNT(*) FROM api_calls WHERE called_at >= %s", (since,))
                result[key] = cur.fetchone()[0]
        return result
