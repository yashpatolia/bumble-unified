import datetime as _dt

from db.base import BaseQueries


class ActivityQueries(BaseQueries):
    """Periodic online-member snapshots (`online_snapshots`), backing the panel's activity graph."""

    def record_online_snapshot(self, guild_key: str, online_count: int) -> None:
        now = _dt.datetime.now(_dt.timezone.utc)
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO online_snapshots (guild_key, taken_at, online_count) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (guild_key, now, online_count),
            )
            # Keep 30 days; the graph only reads the last 24h-7d.
            cur.execute("DELETE FROM online_snapshots WHERE taken_at < %s", (now - _dt.timedelta(days=30),))

    def get_online_activity(self, guild_key: str, hours: int = 24) -> list:
        """Returns [(hour_start, peak_online_in_that_hour), ...] oldest first, for the last `hours` hours."""
        since = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=hours)
        with self._cursor() as cur:
            cur.execute(
                "SELECT date_trunc('hour', taken_at) AS h, MAX(online_count) "
                "FROM online_snapshots WHERE guild_key = %s AND taken_at >= %s "
                "GROUP BY h ORDER BY h",
                (guild_key, since),
            )
            return cur.fetchall()
