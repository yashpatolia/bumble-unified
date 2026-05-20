import logging
import sqlite3
from lib.fetch import request


def get_username(uuid: str) -> str | None:
    """Resolve a UUID to a Minecraft username, using the local DB as a cache."""
    try:
        with sqlite3.connect("bumble.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ign FROM users WHERE uuid = ?", (uuid,))
            row = cursor.fetchone()
            if row:
                return row[0]

            ign = request(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}")["name"]
            existing = cursor.execute("SELECT uuid FROM users WHERE ign = ?", (ign,)).fetchone()
            if existing:
                cursor.execute("UPDATE users SET ign = ? WHERE uuid = ?", (ign.lower(), uuid))
            else:
                cursor.execute("INSERT INTO users (uuid, ign) VALUES (?, ?)", (uuid, ign.lower()))
            conn.commit()
            return ign
    except Exception as e:
        logging.error(e)
        return None
