#!/usr/bin/env python3
"""One-time migration: copy all data from bumble.db (SQLite) to PostgreSQL.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate_sqlite_to_pg.py [path/to/bumble.db]
"""
import os
import sqlite3
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

_DEFAULT_DB = Path(__file__).parent.parent / "bumble.db"


def migrate(sqlite_path: str, dsn: str) -> None:
    src = sqlite3.connect(sqlite_path)
    dst = psycopg2.connect(dsn)
    src.row_factory = sqlite3.Row
    try:
        sc = src.cursor()
        with dst.cursor() as dc:
            # users
            sc.execute("SELECT uuid, ign, discord_id, discord_name FROM users")
            rows = sc.fetchall()
            if rows:
                execute_values(dc,
                    "INSERT INTO users (uuid, ign, discord_id, discord_name) VALUES %s ON CONFLICT DO NOTHING",
                    [(r["uuid"], r["ign"], r["discord_id"], r["discord_name"]) for r in rows])
                print(f"  users: {len(rows)} rows")

            # dyes
            sc.execute("SELECT dye_id, dye_name, weight, hex FROM dyes")
            rows = sc.fetchall()
            if rows:
                execute_values(dc,
                    "INSERT INTO dyes (dye_id, dye_name, weight, hex) VALUES %s ON CONFLICT DO NOTHING",
                    [(r["dye_id"], r["dye_name"], r["weight"], r["hex"]) for r in rows])
                print(f"  dyes: {len(rows)} rows")

            # users_dyes
            sc.execute("SELECT uuid, dye_id, received FROM users_dyes")
            rows = sc.fetchall()
            if rows:
                execute_values(dc,
                    "INSERT INTO users_dyes (uuid, dye_id, received) VALUES %s ON CONFLICT DO NOTHING",
                    [(r["uuid"], r["dye_id"], r["received"]) for r in rows])
                print(f"  users_dyes: {len(rows)} rows")

            # panel_users
            sc.execute("SELECT discord_id, discord_name, is_admin, can_view_logs, can_control_bots FROM panel_users")
            rows = sc.fetchall()
            if rows:
                execute_values(dc,
                    "INSERT INTO panel_users (discord_id, discord_name, is_admin, can_view_logs, can_control_bots) VALUES %s ON CONFLICT DO NOTHING",
                    [(r["discord_id"], r["discord_name"], bool(r["is_admin"]), bool(r["can_view_logs"]), bool(r["can_control_bots"])) for r in rows])
                print(f"  panel_users: {len(rows)} rows")

            # guild_members
            try:
                sc.execute("SELECT guild_key, ign, uuid, rank, skyblock_level, last_login, stats_fetched_at FROM guild_members")
                rows = sc.fetchall()
                if rows:
                    execute_values(dc,
                        "INSERT INTO guild_members (guild_key, ign, uuid, rank, skyblock_level, last_login, stats_fetched_at) VALUES %s ON CONFLICT DO NOTHING",
                        [(r["guild_key"], r["ign"], r["uuid"], r["rank"], r["skyblock_level"], r["last_login"], r["stats_fetched_at"]) for r in rows])
                    print(f"  guild_members: {len(rows)} rows")
            except Exception as e:
                print(f"  guild_members: skipped ({e})")

        dst.commit()
        print("Migration complete.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_DB)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL env var not set")
        sys.exit(1)
    print(f"Migrating {db_path} -> PostgreSQL...")
    migrate(db_path, dsn)
