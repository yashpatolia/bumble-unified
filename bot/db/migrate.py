import logging
import os
from pathlib import Path

import psycopg2

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations(dsn: str) -> None:
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version    INTEGER PRIMARY KEY,
                    name       TEXT NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.execute("SELECT version FROM schema_migrations")
            applied = {r[0] for r in cur.fetchall()}
            for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
                version = int(path.stem.split("_")[0])
                if version not in applied:
                    cur.execute(path.read_text())
                    cur.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                        (version, path.name),
                    )
                    conn.commit()
                    logging.info(f"Applied migration: {path.name}")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dsn = os.environ["DATABASE_URL"]
    run_migrations(dsn)
    logging.info("Migrations complete.")
