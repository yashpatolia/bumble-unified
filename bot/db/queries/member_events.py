from typing import Optional

from psycopg2.extras import Json

from db.base import BaseQueries


def insert_event(cur, guild_key: str, ign: str, kind: str, uuid: Optional[str] = None, detail: Optional[dict] = None) -> None:
    """Writes one roster event using an open cursor. A missing uuid is looked up from the roster,
    then from the users cache, so events are keyed by the stable id whenever it is known."""
    if not uuid:
        cur.execute("SELECT uuid FROM guild_members WHERE guild_key = %s AND LOWER(ign::TEXT) = LOWER(%s)", (guild_key, ign))
        row = cur.fetchone()
        uuid = row[0] if row and row[0] else None
    if not uuid:
        cur.execute("SELECT uuid FROM users WHERE LOWER(ign) = LOWER(%s)", (ign,))
        row = cur.fetchone()
        uuid = row[0] if row and row[0] else None
    cur.execute(
        "INSERT INTO member_events (guild_key, uuid, ign, kind, detail) VALUES (%s, %s, %s, %s, %s)",
        (guild_key, uuid, ign, kind, Json(detail or {})),
    )


class MemberEventsQueries(BaseQueries):
    """Join, leave, rank and rename history (`member_events`) for the member page."""

    def record_member_event(self, guild_key: str, ign: str, kind: str, uuid: Optional[str] = None, detail: Optional[dict] = None) -> None:
        with self._cursor() as cur:
            insert_event(cur, guild_key, ign, kind, uuid, detail)

    def get_member_events(self, guild_key: str, ign: str, uuid: Optional[str], limit: int = 100) -> list:
        """[(occurred_at, guild_key, ign, kind, detail), ...] newest first, across every guild the
        player has been in (matched by uuid, plus this guild's rows for the current name)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT occurred_at, guild_key, ign, kind, detail FROM member_events "
                "WHERE (%s IS NOT NULL AND uuid = %s) OR (guild_key = %s AND LOWER(ign) = LOWER(%s)) "
                "ORDER BY occurred_at DESC, id DESC LIMIT %s",
                (uuid, uuid, guild_key, ign, limit),
            )
            return cur.fetchall()
