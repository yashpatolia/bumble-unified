from typing import Optional

from db.base import BaseQueries


class UsersQueries(BaseQueries):
    """Discord <-> Minecraft account links (the `users` table)."""

    def get_user_by_discord(self, discord_id: int) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_user_by_ign(self, ign: str) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE LOWER(ign) = LOWER(%s)",
                (ign,),
            )
            return cur.fetchone()

    def get_ign(self, discord_id: int) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT ign FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_uuid_by_discord(self, discord_id: int) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT uuid FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_discord_id_by_uuid(self, uuid: str) -> Optional[int]:
        with self._cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_user_by_uuid(self, uuid: str) -> Optional[tuple]:
        """Returns (ign, discord_id, discord_name, discord_avatar) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_id, discord_name, discord_avatar FROM users WHERE uuid = %s",
                (uuid,),
            )
            return cur.fetchone()

    def search_users_with_dye_counts(self, query: str, limit: int = 20) -> list[tuple]:
        """Returns [(uuid, ign, discord_id, discord_name, discord_avatar, unlocked_count), ...]
        for users whose IGN matches query, ordered by IGN."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT u.uuid, u.ign, u.discord_id, u.discord_name, u.discord_avatar, "
                "COUNT(ud.dye_id) FILTER (WHERE ud.received) AS unlocked_count "
                "FROM users u "
                "LEFT JOIN users_dyes ud ON ud.uuid = u.uuid "
                "WHERE u.ign ILIKE %s "
                "GROUP BY u.uuid "
                "ORDER BY u.ign "
                "LIMIT %s",
                (f"%{query}%", limit),
            )
            return cur.fetchall()

    def is_linked(self, uuid: str) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            return row is not None and row[0] is not None

    def link_user(self, uuid: str, ign: str, discord_id: int, discord_name: str, discord_avatar: str = None) -> None:
        """Insert a new user or update an existing record with Discord info."""
        with self._cursor() as cur:
            # Clear any previous link for this discord_id so one Discord account maps to exactly one UUID
            cur.execute(
                "UPDATE users SET discord_id = NULL, discord_name = NULL WHERE discord_id = %s AND uuid != %s",
                (discord_id, uuid),
            )
            cur.execute("SELECT uuid FROM users WHERE uuid = %s", (uuid,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE users SET discord_id = %s, discord_name = %s, discord_avatar = COALESCE(%s, discord_avatar) WHERE uuid = %s",
                    (discord_id, discord_name, discord_avatar, uuid),
                )
            else:
                cur.execute(
                    "INSERT INTO users (uuid, ign, discord_id, discord_name, discord_avatar) VALUES (%s, %s, %s, %s, %s)",
                    (uuid, ign, discord_id, discord_name, discord_avatar),
                )

    def unlink_user(self, uuid: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET discord_id = NULL, discord_name = NULL WHERE uuid = %s",
                (uuid,),
            )

    def update_user_avatar(self, discord_id: int, discord_avatar: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET discord_avatar = %s WHERE discord_id = %s",
                (discord_avatar, discord_id),
            )
