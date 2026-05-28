import sqlite3
from contextlib import contextmanager
from typing import Optional


class DatabaseManager:
    """Centralized SQLite access. All connections have foreign keys enabled."""

    def __init__(self, db_path: str = "bumble.db"):
        self.db_path = db_path

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn

    # --- Users ---

    def get_user_by_discord(self, discord_id: int) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self.connection() as conn:
            return conn.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE discord_id = ?", (discord_id,)
            ).fetchone()

    def get_user_by_ign(self, ign: str) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self.connection() as conn:
            return conn.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE ign = ?", (ign,)
            ).fetchone()

    def get_ign(self, discord_id: int) -> Optional[str]:
        with self.connection() as conn:
            row = conn.execute("SELECT ign FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
            return row[0] if row else None

    def get_uuid_by_discord(self, discord_id: int) -> Optional[str]:
        with self.connection() as conn:
            row = conn.execute("SELECT uuid FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
            return row[0] if row else None

    def get_discord_id_by_uuid(self, uuid: str) -> Optional[int]:
        with self.connection() as conn:
            row = conn.execute("SELECT discord_id FROM users WHERE uuid = ?", (uuid,)).fetchone()
            return row[0] if row else None

    def is_linked(self, uuid: str) -> bool:
        with self.connection() as conn:
            row = conn.execute("SELECT discord_id FROM users WHERE uuid = ?", (uuid,)).fetchone()
            return row is not None and row[0] is not None

    def link_user(self, uuid: str, ign: str, discord_id: int, discord_name: str) -> None:
        """Insert a new user or update an existing record with Discord info."""
        with self.connection() as conn:
            existing = conn.execute("SELECT uuid FROM users WHERE uuid = ?", (uuid,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET discord_id = ?, discord_name = ? WHERE uuid = ?",
                    (discord_id, discord_name, uuid)
                )
            else:
                conn.execute(
                    "INSERT INTO users (uuid, ign, discord_id, discord_name) VALUES (?, ?, ?, ?)",
                    (uuid, ign.lower(), discord_id, discord_name)
                )

    # --- Dyes ---

    def get_dye_info(self, dye_id: str) -> Optional[tuple]:
        """Returns (hex, dye_name) or None."""
        with self.connection() as conn:
            return conn.execute(
                "SELECT hex, dye_name FROM dyes WHERE dye_id = ?", (dye_id,)
            ).fetchone()

    def get_unlocked_dyes(self, uuid: str) -> list[str]:
        """Returns list of dye_id strings the user has received."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT dye_id FROM users_dyes WHERE uuid = ? AND received = TRUE", (uuid,)
            ).fetchall()
            return [row[0] for row in rows]

    def get_all_dyes_weighted(self) -> list[tuple]:
        """Returns [(dye_id, weight), ...] for all dyes."""
        with self.connection() as conn:
            return conn.execute("SELECT dye_id, weight FROM dyes").fetchall()

    def get_dye_received(self, uuid: str, dye_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT received FROM users_dyes WHERE dye_id = ? AND uuid = ?", (dye_id, uuid)
            ).fetchone()
            return bool(row[0]) if row else False

    def get_dye_details(self, dye_id: str) -> Optional[tuple]:
        """Returns (dye_name, weight, hex) or None."""
        with self.connection() as conn:
            return conn.execute(
                "SELECT dye_name, weight, hex FROM dyes WHERE dye_id = ?", (dye_id,)
            ).fetchone()

    def mark_dye_received(self, uuid: str, dye_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE users_dyes SET received = TRUE WHERE dye_id = ? AND uuid = ?", (dye_id, uuid)
            )

    def add_dye(self, dye_id: str, dye_name: str, weight: float, hex_color: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO dyes (dye_id, dye_name, weight, hex) VALUES (?, ?, ?, ?)",
                (dye_id, dye_name.title(), weight, hex_color.capitalize())
            )

    def remove_dye(self, dye_id: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM dyes WHERE dye_id = ?", (dye_id,))

    # --- Guild Members ---

    def setup_guild_member_tables(self) -> None:
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_members (
                    guild_key        TEXT NOT NULL,
                    ign              TEXT NOT NULL,
                    uuid             TEXT,
                    rank             TEXT NOT NULL DEFAULT '',
                    skyblock_level   REAL,
                    last_login       INTEGER,
                    stats_fetched_at INTEGER,
                    PRIMARY KEY (guild_key, ign)
                )
            """)
            for col, typ in [
                ("uuid", "TEXT"),
                ("skyblock_level", "REAL"),
                ("last_login", "INTEGER"),
                ("stats_fetched_at", "INTEGER"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE guild_members ADD COLUMN {col} {typ}")
                except Exception:
                    pass

    def get_guild_members(self, guild_key: str) -> list:
        with self.connection() as conn:
            return conn.execute(
                "SELECT ign, rank, skyblock_level, last_login FROM guild_members "
                "WHERE guild_key = ? ORDER BY ign COLLATE NOCASE",
                (guild_key,)
            ).fetchall()

    def get_guild_members_with_uuid(self, guild_key: str) -> list:
        with self.connection() as conn:
            return conn.execute(
                "SELECT ign, uuid FROM guild_members WHERE guild_key = ?",
                (guild_key,)
            ).fetchall()

    def upsert_guild_member(self, guild_key: str, ign: str, rank: str = '') -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO guild_members (guild_key, ign, rank) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_key, ign) DO UPDATE SET rank = excluded.rank",
                (guild_key, ign, rank)
            )

    def remove_guild_member(self, guild_key: str, ign: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM guild_members WHERE guild_key = ? AND ign = ? COLLATE NOCASE",
                (guild_key, ign)
            )

    def sync_guild_members(self, guild_key: str, members: list) -> None:
        with self.connection() as conn:
            # Remove members no longer in guild
            existing = {r[0] for r in conn.execute("SELECT ign FROM guild_members WHERE guild_key = ?", (guild_key,)).fetchall()}
            new_igns = {m['ign'] for m in members}
            for ign in existing - new_igns:
                conn.execute("DELETE FROM guild_members WHERE guild_key = ? AND ign = ? COLLATE NOCASE", (guild_key, ign))
            # Upsert, preserving stats columns
            conn.executemany(
                "INSERT INTO guild_members (guild_key, ign, uuid, rank) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(guild_key, ign) DO UPDATE SET uuid = excluded.uuid, rank = excluded.rank",
                [(guild_key, m['ign'], m.get('uuid', ''), m.get('rank', '')) for m in members]
            )

    def update_guild_member_stats(self, guild_key: str, ign: str, skyblock_level, last_login) -> None:
        import time as _time
        with self.connection() as conn:
            conn.execute(
                "UPDATE guild_members SET skyblock_level = ?, last_login = ?, stats_fetched_at = ? "
                "WHERE guild_key = ? AND ign = ? COLLATE NOCASE",
                (skyblock_level, last_login, int(_time.time()), guild_key, ign)
            )

    def update_guild_member_uuid(self, guild_key: str, ign: str, uuid: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE guild_members SET uuid = ? WHERE guild_key = ? AND ign = ? COLLATE NOCASE",
                (uuid, guild_key, ign)
            )

    # --- Panel Users ---

    def setup_panel_tables(self) -> None:
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS panel_users (
                    discord_id       INTEGER PRIMARY KEY,
                    discord_name     TEXT NOT NULL,
                    is_admin         INTEGER DEFAULT 0,
                    can_view_logs    INTEGER DEFAULT 1,
                    can_control_bots INTEGER DEFAULT 0,
                    can_fetch_api    INTEGER DEFAULT 0
                )
            """)
            # Migrate existing tables that lack new columns
            try:
                conn.execute("ALTER TABLE panel_users ADD COLUMN can_control_bots INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE panel_users ADD COLUMN can_fetch_api INTEGER DEFAULT 0")
            except Exception:
                pass

    def get_panel_user(self, discord_id: int) -> Optional[tuple]:
        """Returns (discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api) or None."""
        with self.connection() as conn:
            return conn.execute(
                "SELECT discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api FROM panel_users WHERE discord_id = ?",
                (discord_id,)
            ).fetchone()

    def get_all_panel_users(self) -> list:
        with self.connection() as conn:
            return conn.execute(
                "SELECT discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api FROM panel_users"
            ).fetchall()

    def create_panel_user(self, discord_id: int, discord_name: str, is_admin: bool = False, can_view_logs: bool = True, can_control_bots: bool = False, can_fetch_api: bool = False) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO panel_users (discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api) VALUES (?, ?, ?, ?, ?, ?)",
                (discord_id, discord_name, int(is_admin), int(can_view_logs), int(can_control_bots), int(can_fetch_api))
            )

    def upsert_panel_user_name(self, discord_id: int, discord_name: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE panel_users SET discord_name = ? WHERE discord_id = ?",
                (discord_name, discord_id)
            )

    def update_panel_user_permissions(self, discord_id: int, is_admin: bool, can_view_logs: bool, can_control_bots: bool, can_fetch_api: bool = False) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE panel_users SET is_admin = ?, can_view_logs = ?, can_control_bots = ?, can_fetch_api = ? WHERE discord_id = ?",
                (int(is_admin), int(can_view_logs), int(can_control_bots), int(can_fetch_api), discord_id)
            )

    def delete_panel_user(self, discord_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM panel_users WHERE discord_id = ?", (discord_id,))
