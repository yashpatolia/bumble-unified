import datetime as _dt
from typing import Optional

from db.base import BaseQueries


class ExcusedQueries(BaseQueries):
    """Officer-excused members (`excused_members`), skipped by the panel's inactivity warnings."""

    def get_excused(self, guild_key: str) -> dict:
        """Returns {lowercase_ign: {reason, until, by}} for excusals that have not expired."""
        today = _dt.date.today()
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign::TEXT, reason, until_date, created_by FROM excused_members "
                "WHERE guild_key = %s AND (until_date IS NULL OR until_date >= %s)",
                (guild_key, today),
            )
            return {
                row[0].lower(): {"reason": row[1], "until": row[2].isoformat() if row[2] else None, "by": row[3]}
                for row in cur.fetchall()
            }

    def set_excused(self, guild_key: str, ign: str, reason: Optional[str], until: Optional[_dt.date], created_by: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO excused_members (guild_key, ign, reason, until_date, created_by, created_at) "
                "VALUES (%s, %s, %s, %s, %s, NOW()) "
                "ON CONFLICT (guild_key, ign) DO UPDATE SET reason = EXCLUDED.reason, until_date = EXCLUDED.until_date, "
                "created_by = EXCLUDED.created_by, created_at = NOW()",
                (guild_key, ign, reason, until, created_by),
            )

    def remove_excused(self, guild_key: str, ign: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM excused_members WHERE guild_key = %s AND ign = %s", (guild_key, ign))
