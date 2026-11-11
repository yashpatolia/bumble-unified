import datetime

from db.base import BaseQueries


class MutesQueries(BaseQueries):
    """Active guild mutes (`guild_mutes`), used to mirror them as Discord timeouts."""

    def record_mute(self, guild_key: str, ign: str, duration: datetime.timedelta) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO guild_mutes (guild_key, ign, muted_at, expires_at)
                VALUES (%s, %s, NOW(), NOW() + %s)
                ON CONFLICT (guild_key, ign) DO UPDATE SET muted_at = NOW(), expires_at = EXCLUDED.expires_at
                """,
                (guild_key, ign, duration),
            )

    def clear_mute(self, guild_key: str, ign: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM guild_mutes WHERE guild_key = %s AND ign = %s", (guild_key, ign))

    def get_mutes(self) -> list[tuple]:
        """[(guild_key, ign, expires_at), ...] for every recorded mute, expired or not."""
        with self._cursor() as cur:
            cur.execute("SELECT guild_key, ign::TEXT, expires_at FROM guild_mutes")
            return cur.fetchall()
