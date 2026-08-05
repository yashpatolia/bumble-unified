from typing import Optional

from db.base import BaseQueries


class DyesQueries(BaseQueries):
    """Dye catalog and per-player unlocks (`dyes` / `users_dyes`)."""

    def get_dye_info(self, dye_id: str) -> Optional[tuple]:
        """Returns (hex, dye_name) or None."""
        with self._cursor() as cur:
            cur.execute("SELECT hex, dye_name FROM dyes WHERE dye_id = %s", (dye_id,))
            return cur.fetchone()

    def get_unlocked_dyes(self, uuid: str) -> list[str]:
        """Returns list of dye_id strings the user has received."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT dye_id FROM users_dyes WHERE uuid = %s AND received = TRUE",
                (uuid,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_all_dyes_weighted(self) -> list[tuple]:
        """Returns [(dye_id, weight), ...] for all dyes."""
        with self._cursor() as cur:
            cur.execute("SELECT dye_id, weight FROM dyes")
            return cur.fetchall()

    def get_all_dyes(self) -> list[tuple]:
        """Returns [(dye_id, dye_name, weight, hex), ...] for all dyes, commonest first."""
        with self._cursor() as cur:
            cur.execute("SELECT dye_id, dye_name, weight, hex FROM dyes ORDER BY weight DESC")
            return cur.fetchall()

    def get_dye_received(self, uuid: str, dye_id: str) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT received FROM users_dyes WHERE dye_id = %s AND uuid = %s",
                (dye_id, uuid),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False

    def get_dye_details(self, dye_id: str) -> Optional[tuple]:
        """Returns (dye_name, weight, hex) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT dye_name, weight, hex FROM dyes WHERE dye_id = %s", (dye_id,)
            )
            return cur.fetchone()

    def mark_dye_received(self, uuid: str, dye_id: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO users_dyes (uuid, dye_id, received, unlocked_at) VALUES (%s, %s, TRUE, NOW()) "
                "ON CONFLICT (uuid, dye_id) DO UPDATE SET received = TRUE, unlocked_at = NOW()",
                (uuid, dye_id),
            )

    def get_recent_drops(self, limit: int = 20) -> list[tuple]:
        """Returns [(dye_id, dye_name, hex, unlocked_at, uuid, ign, discord_name, discord_avatar), ...],
        most recent first."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ud.dye_id, d.dye_name, d.hex, ud.unlocked_at, "
                "u.uuid, u.ign, u.discord_name, u.discord_avatar "
                "FROM users_dyes ud "
                "JOIN dyes d ON d.dye_id = ud.dye_id "
                "JOIN users u ON u.uuid = ud.uuid "
                "WHERE ud.received = TRUE AND ud.unlocked_at IS NOT NULL "
                "ORDER BY ud.unlocked_at DESC "
                "LIMIT %s",
                (limit,),
            )
            return cur.fetchall()

    def add_dye(self, dye_id: str, dye_name: str, weight: float, hex_color: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO dyes (dye_id, dye_name, weight, hex) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (dye_id, dye_name.title(), weight, hex_color.capitalize()),
            )

    def remove_dye(self, dye_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM dyes WHERE dye_id = %s", (dye_id,))

    def reset_all_dye_rolls(self) -> int:
        """Delete every player's dye-unlock records. Returns the number of rows removed."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM users_dyes")
            return cur.rowcount
