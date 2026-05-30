import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
API_KEY = os.getenv("HYPIXEL_API_KEY")

# Web panel
PANEL_PORT = int(os.getenv("PANEL_PORT", "8080"))
BOT_IPC_PORT = int(os.getenv("BOT_IPC_PORT", "8081"))
PANEL_DISCORD_CLIENT_ID = os.getenv("PANEL_DISCORD_CLIENT_ID")
PANEL_DISCORD_CLIENT_SECRET = os.getenv("PANEL_DISCORD_CLIENT_SECRET")
PANEL_REDIRECT_URI = os.getenv("PANEL_REDIRECT_URI")
PANEL_JWT_SECRET = os.getenv("PANEL_JWT_SECRET")
PANEL_ADMIN_DISCORD_ID = int(os.getenv("PANEL_ADMIN_DISCORD_ID", "0"))

SERVER = os.getenv("MINECRAFT_SERVER_IP") or "mc.hypixel.net"
VERSION = os.getenv("MINECRAFT_VERSION") or "1.8.9"

# Webhook URLs (Shared)
BRIDGE_CHANNEL = os.getenv("BRIDGE_CHANNEL")
OFFICER_CHANNEL = os.getenv("OFFICER_CHANNEL")

# Webhook URLs (Per-guild logs)
BK_LOGS_CHANNEL = os.getenv("KINDERGARTEN_LOGS_CHANNEL")
BU_LOGS_CHANNEL = os.getenv("UNIVERSITY_LOGS_CHANNEL")

# Webhook URLs (Other)
DYES_CHANNEL = os.getenv("DYES_CHANNEL")
MESSAGE_LOGS_CHANNEL = os.getenv("MESSAGE_LOGS_CHANNEL")

# Channel IDs
BRIDGE_CHANNEL_ID = int(os.getenv("BRIDGE_CHANNEL_ID"))
OFFICER_CHANNEL_ID = int(os.getenv("OFFICER_CHANNEL_ID"))
LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID"))
DYES_CHANNEL_ID = int(os.getenv("DYES_CHANNEL_ID"))

# Discord Role IDs
BK_STAFF_ROLE = int(os.getenv("BK_STAFF_ROLE_ID"))
BU_STAFF_ROLE = int(os.getenv("BU_STAFF_ROLE_ID"))
BOT_ROLE = int(os.getenv("BOT_ROLE_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))
EXEC_ROLE = int(os.getenv("EXEC_ROLE_ID"))

# Member roles
BK_MEMBER = int(os.getenv("KINDERGARTEN_MEMBER_ROLE_ID"))
BU_MEMBER = int(os.getenv("UNIVERSITY_MEMBER_ROLE_ID"))

# BK rank role IDs
BABY = int(os.getenv("BABY"))
TODDLER = int(os.getenv("TODDLER"))
SWEATY = int(os.getenv("SWEATY"))
ULTIMATE = int(os.getenv("ULTIMATE"))

# BK rank level requirements
BABY_REQ = int(os.getenv("BABY_REQ"))
TODDLER_REQ = int(os.getenv("TODDLER_REQ"))
SWEATY_REQ = int(os.getenv("SWEATY_REQ"))
ULTIMATE_REQ = int(os.getenv("ULTIMATE_REQ"))

# BU rank role IDs
STUDENT = int(os.getenv("STUDENT"))
BACHELOR = int(os.getenv("BACHELOR"))
MASTER = int(os.getenv("MASTER"))
DOCTOR = int(os.getenv("DOCTOR"))

# BU rank level requirements
STUDENT_REQ = int(os.getenv("STUDENT_REQ"))
BACHELOR_REQ = int(os.getenv("BACHELOR_REQ"))
MASTER_REQ = int(os.getenv("MASTER_REQ"))
DOCTOR_REQ = int(os.getenv("DOCTOR_REQ"))

BK_GUILD_RANKS = {'Baby': BABY_REQ, 'Tot': TODDLER_REQ, 'Sweat': SWEATY_REQ, 'Pro': ULTIMATE_REQ}
BU_GUILD_RANKS = {'Junior': STUDENT_REQ, 'Bach': BACHELOR_REQ, 'Master': MASTER_REQ, 'Dctr': DOCTOR_REQ}

BK_OPTIONS = {"host": SERVER, "username": os.getenv("KINDERGARTEN_USERNAME"), "auth": "microsoft", "version": VERSION, "hideErrors": False}
BU_OPTIONS = {"host": SERVER, "username": os.getenv("UNIVERSITY_USERNAME"), "auth": "microsoft", "version": VERSION, "hideErrors": False}


@dataclass
class GuildConfig:
    """Immutable configuration for a single Minecraft guild."""
    key: str                            # 'bk' or 'bu'
    display_name: str                   # 'Bumble Kindergarten'
    short_name: str                     # 'BK'
    mc_options: dict                    # Mineflayer connection options
    guild_name: str                     # Hypixel guild name (for /guild list matching)
    staff_role_id: int                  # Discord staff role
    member_role_id: int                 # Discord member role
    ranks: dict                         # {bot_rank_key: skyblock_level_req}
    discord_rank_map: dict              # {Hypixel guild rank → bot rank key}
    bridge_channel_id: Optional[int]    # Discord channel that feeds this MC guild (None = no listener)
    officer_channel_id: Optional[int]   # Officer channel (None = no listener)

    @property
    def mc_username(self) -> str:
        return self.mc_options.get("username", "")


BK_CONFIG = GuildConfig(
    key='bk',
    display_name='Bumble Kindergarten',
    short_name='BK',
    mc_options=BK_OPTIONS,
    guild_name=os.getenv("KINDERGARTEN_GUILD_NAME", "Bumble Kindergarten"),
    staff_role_id=BK_STAFF_ROLE,
    member_role_id=BK_MEMBER,
    ranks=BK_GUILD_RANKS,
    discord_rank_map={'Baby Bee': 'Baby', 'Toddler Bee': 'Tot', 'Sweaty Bee': 'Sweat', 'Ultimate Bee': 'Pro'},
    bridge_channel_id=BRIDGE_CHANNEL_ID,
    officer_channel_id=OFFICER_CHANNEL_ID,
)

BU_CONFIG = GuildConfig(
    key='bu',
    display_name='Bumble University',
    short_name='BU',
    mc_options=BU_OPTIONS,
    guild_name=os.getenv("UNIVERSITY_GUILD_NAME", "Bumble University"),
    staff_role_id=BU_STAFF_ROLE,
    member_role_id=BU_MEMBER,
    ranks=BU_GUILD_RANKS,
    discord_rank_map={'Student': 'Junior', 'Bachelor': 'Bach', 'Master': 'Master', 'Doctorate': 'Dctr'},
    bridge_channel_id=None,    # BU messages come from BK's shared Discord channel
    officer_channel_id=None,
)

# Ordered dict of all guild configs — add new guilds here to scale
GUILD_CONFIGS: dict[str, GuildConfig] = {
    'bk': BK_CONFIG,
    'bu': BU_CONFIG,
}
