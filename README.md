# Bumble Bridge Bot

A Discord bot that bridges two Hypixel Skyblock Minecraft guilds — **Bumble Kindergarten (BK)** and **Bumble University (BU)** — with a shared Discord server and a web management panel.

## Features

### Guild Bridge
- Relays chat between Minecraft guild chat and Discord in real time (both directions)
- Cross-relays messages between the two guilds in-game with `[BK]`/`[BU]` prefixes
- Announces system events (joins, leaves, kicks, mutes, promotions, demotions) as Discord embeds
- Posts join requests with the applicant's Skyblock level for quick staff review

### In-Game Dot Commands
Players can type commands in guild chat to query Hypixel Skyblock stats:

| Command | Description |
|---------|-------------|
| `.lvl <player>` | Skyblock level |
| `.cata <player>` | Catacombs level, secrets, S/S+/R clears |
| `.nw <player>` | Net worth (via skyhelper-networth) |
| `.slayer <player>` | Claimed slayer levels for all boss types |
| `.mp <player>` | Magical power (decodes talisman bag NBT) |
| `.pb <player>` | Personal best dungeon floor times |
| `.bank <player>` | Bank and purse balance |
| `.ranks` | Auto-promotes/demotes all guild members by Skyblock level |

### Discord Slash Commands
- `/bk-guild` / `/bu-guild` — list members, mute, kick, invite, promote, demote
- `/link` — self-service Discord ↔ Minecraft account linking via Hypixel social media
- `/dyes` — claim a color role from armor dyes you've received
- `/apply` — open a private application ticket channel
- `/admin` — add or remove dye drops (exec role only)
- `/bk-exec` / `/bu-exec` — run raw Minecraft commands (exec role only)

### Armor Dye Tracking
- Weighted random dye drop system with per-player history
- Assigns Discord color roles when a player receives a new dye

### Web Management Panel
- React + FastAPI panel with real-time log streaming over WebSocket
- Discord OAuth2 login with JWT sessions
- Dashboard to start, stop, and restart each Minecraft bot
- Admin panel to manage panel users and their permissions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Discord bot | Python, discord.py |
| Minecraft client | Node.js, Mineflayer |
| Python ↔ Node bridge | `javascript` (JSPyBridge) |
| Player data | Hypixel API, skyhelper-networth |
| Web backend | FastAPI, uvicorn |
| Web frontend | React, TypeScript, Vite |
| Auth | Discord OAuth2, JWT (HS256) |
| Database | SQLite3 |
| Deployment | VPS, single `deploy.sh` script |

## Architecture

```
Discord Server
    │
    │  webhooks (SyncWebhook)        slash commands (app_commands)
    ▼                                        ▼
Client (main.py)  ◄───────────────  cogs/commands/*.py
    │                                        │
    │  guilds_state['bk'].bot                │  db/manager.py (SQLite)
    │  guilds_state['bu'].bot                │
    ▼                                        ▼
Mineflayer bots (Node.js)           bumble.db (SQLite3)
    │
    │  On("chat") / On("messagestr")
    ▼
cogs/bridge/bridge.py       →  utils/command_handler.py  →  player/*.py  →  Hypixel API
cogs/bridge/message_handler.py
cogs/bridge/connections.py
```

Two Mineflayer bots run concurrently — one per guild. Each has its own `GuildConfig` (ranks, role IDs, channel IDs) and `GuildState` (live bot instance, buffers). Bridge cogs are automatically reloaded on reconnect so new Mineflayer event bindings attach to the fresh bot instance.

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Hypixel API key
- Two Microsoft accounts for the Minecraft bots
- A Discord application with a bot token and OAuth2 credentials

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/bumble-unified.git
cd bumble-unified

# Install Python dependencies
pip install -r bot/requirements.txt

# Install Node dependencies
cd bot && npm install && cd ..

# Build the frontend (optional — only needed for the web panel)
cd frontend && npm install && npm run build && cd ..

# Configure environment
cp example.env .env
# Fill in all values in .env
```

### Running

```bash
# Start the bot + web panel
python bot/main.py
```

Or use the deploy script on a VPS:

```bash
./deploy.sh
```

## Configuration

All configuration lives in `.env` (copy from `example.env`). Key variables:

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal |
| `HYPIXEL_API_KEY` | Hypixel API key |
| `KINDERGARTEN_USERNAME` / `UNIVERSITY_USERNAME` | Microsoft account usernames for Minecraft bots |
| `BRIDGE_CHANNEL` | Shared bridge webhook URL |
| `PANEL_DISCORD_CLIENT_ID` / `PANEL_DISCORD_CLIENT_SECRET` | Discord OAuth2 app credentials |
| `PANEL_JWT_SECRET` | Random secret for signing JWTs |
| `PANEL_ADMIN_DISCORD_ID` | Your Discord user ID — auto-created as admin on first login |

See `example.env` for the full list.

## Project Structure

```
bumble-unified/
├── bot/
│   ├── main.py                # Entry point — Discord client, cog loading
│   ├── config.py              # All config + GuildConfig dataclass
│   ├── constants.py           # Dungeon XP tables, dye IDs, MP values
│   ├── db/                    # SQLite DatabaseManager
│   ├── lib/                   # Utility functions (fetch, UUID cache, rank changes)
│   ├── player/                # Hypixel Skyblock player data (level, cata, slayers, MP, NW)
│   ├── utils/                 # In-game command dispatcher, dye roll logic
│   ├── web/                   # FastAPI web panel (auth, routes, log broadcaster)
│   └── cogs/
│       ├── bridge/            # MC↔Discord relay, reconnect, system message handler
│       └── commands/          # All Discord slash command cogs
└── frontend/                  # React/Vite web panel UI
```

## Adding a New Guild

1. Add env vars for the MC account, webhook URLs, role IDs, and rank requirements to `.env`
2. Create a new `GuildConfig` in `config.py` and add it to `GUILD_CONFIGS`
3. Add the log webhook URL to `log_urls` in `main.py`
4. Add a new `GroupCog` class in `cogs/commands/guild_commands.py`

Everything else (bridge relay, `.ranks`, auto-reconnect) picks up the new guild automatically.
