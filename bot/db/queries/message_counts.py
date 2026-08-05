import datetime

from db.base import BaseQueries


class MessageCountsQueries(BaseQueries):
    """Per-player message counts (`message_counts`), backing the leaderboard."""

    def increment_message_count(self, guild_key: str, ign: str) -> None:
        """Increment lifetime, current month, and current week counts for a player."""
        now = datetime.datetime.utcnow()
        month_key = now.strftime('%Y-%m')
        week_key = now.strftime('%G-W%V')  # ISO week
        periods = [('lifetime', ''), ('month', month_key), ('week', week_key)]
        with self._cursor() as cur:
            # Resolve UUID and canonical IGN from guild_members (citext match is case-insensitive)
            cur.execute(
                "SELECT uuid, ign::TEXT FROM guild_members WHERE guild_key = %s AND ign = %s",
                (guild_key, ign)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return
            uuid, canonical_ign = row
            for period_type, period_key in periods:
                cur.execute(
                    "INSERT INTO message_counts (guild_key, uuid, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, %s, %s, %s, 1) "
                    "ON CONFLICT (guild_key, uuid, period_type, period_key) WHERE uuid IS NOT NULL AND uuid != '' "
                    "DO UPDATE SET count = message_counts.count + 1, ign = EXCLUDED.ign",
                    (guild_key, uuid, canonical_ign, period_type, period_key)
                )

    def get_message_leaderboard(self, guild_key: str, period_type: str, period_key: str) -> list:
        """Returns [(ign, count, uuid, discord_name, discord_id, discord_avatar), ...] sorted by count desc."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT mc.ign, mc.count, mc.uuid, u.discord_name, u.discord_id, u.discord_avatar "
                "FROM message_counts mc "
                "LEFT JOIN users u ON u.uuid = mc.uuid "
                "WHERE mc.guild_key = %s AND mc.period_type = %s AND mc.period_key = %s "
                "  AND mc.uuid IS NOT NULL AND mc.uuid != '' "
                "ORDER BY mc.count DESC",
                (guild_key, period_type, period_key)
            )
            return cur.fetchall()

    def bulk_increment_message_counts(self, guild_key: str, counts: dict) -> None:
        """counts is {ign: count}. Used for bulk import. Only increments for IGNs in guild_members."""
        with self._cursor() as cur:
            for ign, count in counts.items():
                cur.execute(
                    "SELECT uuid, ign::TEXT FROM guild_members WHERE guild_key = %s AND ign = %s",
                    (guild_key, ign)
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    continue
                uuid, canonical_ign = row
                cur.execute(
                    "INSERT INTO message_counts (guild_key, uuid, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, %s, 'lifetime', '', %s) "
                    "ON CONFLICT (guild_key, uuid, period_type, period_key) WHERE uuid IS NOT NULL AND uuid != '' "
                    "DO UPDATE SET count = message_counts.count + %s, ign = EXCLUDED.ign",
                    (guild_key, uuid, canonical_ign, count, count)
                )
