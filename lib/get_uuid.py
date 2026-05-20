import logging
import sqlite3
from lib.fetch import request


def get_uuid(username: str) -> str | None:
    """Resolve a Minecraft username to a UUID, using the local DB as a cache."""
    try:
        with sqlite3.connect("bumble.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid FROM users WHERE ign = ?", (username.lower(),))
            row = cursor.fetchone()
            if row:
                return row[0]

            uuid = request(f"https://api.mojang.com/users/profiles/minecraft/{username}")["id"]
            existing = cursor.execute("SELECT ign FROM users WHERE uuid = ?", (uuid,)).fetchone()
            if existing:
                cursor.execute("UPDATE users SET ign = ? WHERE uuid = ?", (username.lower(), uuid))
            else:
                cursor.execute("INSERT INTO users (uuid, ign) VALUES (?, ?)", (uuid, username.lower()))
            conn.commit()
            return uuid
    except Exception as e:
        logging.error(e)
        return None
