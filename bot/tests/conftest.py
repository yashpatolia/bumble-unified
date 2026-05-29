"""
Conftest — runs before any test module is imported.

Strategy:
  1. Stub heavy external dependencies via sys.modules so psycopg2, discord,
     and javascript never try to open real connections at import time.
  2. Set every env var that config.py converts with int() so that import
     doesn't blow up with TypeError.
"""
import os
import sys
from unittest.mock import MagicMock

# ── 1. Stub modules that require live services or native extensions ─────────
_STUBS = [
    "psycopg2",
    "psycopg2.pool",
    "psycopg2.extras",
    "javascript",
    "nbt",
    "nbt.nbt",
    # discord and its submodules — only needed if a test imports a cog
    "discord",
    "discord.ext",
    "discord.ext.commands",
    "discord.ext.tasks",
    # HTTP libs — unit tests never make real network calls
    "aiohttp",
    "requests",
    # python-dotenv — load_dotenv becomes a no-op; env vars are set below
    "dotenv",
]
for _mod in _STUBS:
    sys.modules.setdefault(_mod, MagicMock())

# ── 2. Env vars required by config.py ─────────────────────────────────────
_INT_VARS = [
    "BRIDGE_CHANNEL_ID", "OFFICER_CHANNEL_ID", "LOGS_CHANNEL_ID",
    "DYES_CHANNEL_ID", "BK_STAFF_ROLE_ID", "BU_STAFF_ROLE_ID",
    "BOT_ROLE_ID", "OWNER_ID", "EXEC_ROLE_ID",
    "KINDERGARTEN_MEMBER_ROLE_ID", "UNIVERSITY_MEMBER_ROLE_ID",
    # BK ranks
    "BABY", "TODDLER", "SWEATY", "ULTIMATE",
    "BABY_REQ", "TODDLER_REQ", "SWEATY_REQ", "ULTIMATE_REQ",
    # BU ranks
    "STUDENT", "BACHELOR", "MASTER", "DOCTOR",
    "STUDENT_REQ", "BACHELOR_REQ", "MASTER_REQ", "DOCTOR_REQ",
]
for _var in _INT_VARS:
    os.environ.setdefault(_var, "0")

_STR_VARS = {
    "DATABASE_URL": "",
    "HYPIXEL_API_KEY": "test-key",
    "DISCORD_BOT_TOKEN": "test-token",
    "BRIDGE_CHANNEL": "https://discord.com/api/webhooks/0/test",
    "OFFICER_CHANNEL": "https://discord.com/api/webhooks/0/test",
    "KINDERGARTEN_LOGS_CHANNEL": "https://discord.com/api/webhooks/0/test",
    "UNIVERSITY_LOGS_CHANNEL": "https://discord.com/api/webhooks/0/test",
    "DYES_CHANNEL": "https://discord.com/api/webhooks/0/test",
    "MESSAGE_LOGS_CHANNEL": "https://discord.com/api/webhooks/0/test",
}
for _var, _val in _STR_VARS.items():
    os.environ.setdefault(_var, _val)
