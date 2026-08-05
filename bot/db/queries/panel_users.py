from typing import Optional

from db.base import BaseQueries


class PanelUsersQueries(BaseQueries):
    """Web panel access control (`panel_users`) — separate from Discord<->MC links in `users`."""

    def get_panel_user(self, discord_id: int) -> Optional[tuple]:
        """Returns (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_all_panel_users(self) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users"
            )
            return cur.fetchall()

    def create_panel_user(
        self,
        discord_id: int,
        discord_name: str,
        is_admin: bool = False,
        can_control_bots: bool = False,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO panel_users (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links),
            )

    def upsert_panel_user_name(self, discord_id: int, discord_name: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET discord_name = %s WHERE discord_id = %s",
                (discord_name, discord_id),
            )

    def update_panel_user_permissions(
        self,
        discord_id: int,
        is_admin: bool,
        can_control_bots: bool,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET is_admin = %s, can_control_bots = %s, "
                "can_fetch_api = %s, can_manage_links = %s WHERE discord_id = %s",
                (is_admin, can_control_bots, can_fetch_api, can_manage_links, discord_id),
            )

    def delete_panel_user(self, discord_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM panel_users WHERE discord_id = %s", (discord_id,))
