# Bumble

A Discord bot and web panel that bridge two Hypixel Skyblock guilds, **Bumble Kindergarten (BK)** and **Bumble University (BU)**, with their shared Discord server.

## Features

### Guild bridge
- Relays guild and officer chat between Minecraft and Discord in both directions.
- Cross-relays chat between the two guilds in-game with `[BK]` / `[BU]` prefixes.
- Posts joins, leaves, kicks, mutes, promotions, demotions and join requests to Discord as embeds. Join requests include the applicant's Skyblock level.
- Reconnects automatically when a Minecraft bot drops.

### Rank automation
- A background task refreshes one member's stats every 5 seconds, cycling through the whole roster, and promotes or demotes them by Skyblock level.
- New members are ranked a few seconds after they join instead of waiting for the next cycle.
- Rank level requirements can be edited per guild from the web panel.

### In-game commands
Anyone in guild chat (or the Discord bridge channel) can run these. The username defaults to the sender.

| Command | Description |
|---------|-------------|
| `.lvl [user]` / `.hlvl [user]` | Skyblock level on the selected profile / highest across profiles |
| `.nw [user]` | Networth and non-cosmetic networth |
| `.sacks [user]` / `.sax [user]` | Total value of everything in the player's sacks |
| `.bank [user]` | Coop bank, personal bank and purse |
| `.cata [user]` | Catacombs level, secrets and secrets per run |
| `.rtc [user] [level] [floor]` | Runs to a Catacombs level |
| `.rtca [user] [floor]` | Runs to class average 50 (defaults to M7) |
| `.rtcaf [user] <classes> [floor]` | Same as `.rtca`, but never plays the listed classes |
| `.pb [user] (f/m)(1-7)` | Personal best times for a floor |
| `.slayer [user]` / `.slayerxp [user] <type>` | Slayer levels / XP for one boss |
| `.mp [user]` | Magical power |
| `.chim <looting> <mf>` | Chimera drop chance |
| `.petscore [user]` | Pet score |
| `.warpout [ign]` | The BU bot joins SkyBlock, parties the player and `/p warp`s them to it, then returns to the lobby. Requests queue (needs the bot on 26.1) |
| `.help` | Lists commands |

Networth and sack values come from [skyhelper-networth](https://www.npmjs.com/package/skyhelper-networth).

### Discord slash commands
| Command | Who | Description |
|---------|-----|-------------|
| `/bk-guild`, `/bu-guild` | Staff | List, invite, kick, mute, unmute, promote and demote members |
| `/link` | Everyone | Link your Discord to your Minecraft account (verified through Hypixel social links) |
| `/dyes` | Everyone | Pick a colour role from the armor dyes you've collected |
| `/apply` | Everyone | Open a private application ticket |
| `/user`, `/staff link` | Staff | Look up or force-link an account |
| `/admin`, `/bk-exec`, `/bu-exec` | Exec | Manage dyes, run raw Minecraft commands |

### Armor dyes
Every guild chat message has a small chance to drop a dye. Each player's collection is tracked, new drops are announced in-game and on Discord, and collected dyes unlock Discord colour roles.

### Web panel
React panel with Discord login (and a read-only guest mode):
- **Overview**: connection status, member count, live chat and online-member history.
- **Members**: the full roster with level, 90-day level change, last login, chat activity, linked Discord account and "needs attention" flags (inactive, kick risk, stale stats). Staff can kick, invite, excuse members and link accounts.
- **Leaderboard**: message counts for lifetime, this month and this week.
- **Config**: rank requirements, attention thresholds and activity tiers per guild.
- **Dyes**: your collection, other players' collections and recent drops.
- **Admin / Users**: start, stop and restart the bots, refresh stats, view Hypixel API usage, and manage panel users and their permissions.

## Architecture

The bot and the panel are two separate processes. They share PostgreSQL, and the panel reaches the bot's live state through a small HTTP API that only listens on localhost.

```
bot/main.py  (bot process)                bot/web_main.py  (panel process)
  Discord client + slash commands            FastAPI panel
  Mineflayer bots (one per guild)            serves frontend/dist
  background tasks                           │
  IPC API on 127.0.0.1:BOT_IPC_PORT  ◄───────┘  HTTP + X-IPC-Secret
          │                                       │
          └──────────────► PostgreSQL ◄───────────┘
```

Either process can be restarted without the other. Both apply database migrations on startup.

| Layer | Technology |
|-------|-----------|
| Discord bot | Python, discord.py |
| Minecraft client | Mineflayer (Node.js), driven from Python through [JSPyBridge](https://github.com/extremeheat/JSPyBridge) |
| Player data | Hypixel API, skyhelper-networth |
| Panel backend | FastAPI, uvicorn, Discord OAuth2 + JWT |
| Panel frontend | React, TypeScript, Vite |
| Database | PostgreSQL |

## Project structure

```
bumble-unified/
├── bot/
│   ├── main.py            # Bot process entry point
│   ├── web_main.py        # Panel process entry point
│   ├── bot_ipc.py         # Internal API the panel calls
│   ├── config.py          # Env config + per-guild GuildConfig
│   ├── constants.py       # Static game data (XP tables, dyes, boosts)
│   ├── cogs/              # Discord cogs: bridge, slash commands, background tasks
│   ├── db/                # Database access and numbered SQL migrations
│   ├── lib/               # Small helpers (HTTP, UUID cache, rank changes, panel settings)
│   ├── player/            # Skyblock stat calculations
│   ├── utils/             # In-game command dispatcher, dye rolls
│   └── web/               # Panel API routes and auth
├── frontend/              # React panel
├── scripts/               # Dev tooling (copy prod DB)
├── docs/DEVELOPMENT.md    # Local development notes
└── deploy.sh              # VPS deploy script
```

[CLAUDE.md](CLAUDE.md) has the detailed per-file reference.

## Setup

### Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL
- A Hypixel API key
- Two Microsoft accounts that own Minecraft (one per guild bot)
- A Discord application with a bot token and OAuth2 credentials

### Install

```bash
git clone https://github.com/yashpatolia/bumble-unified.git
cd bumble-unified

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r bot/requirements.txt

(cd bot && npm install)
(cd frontend && npm install && npm run build)

cp example.env .env               # then fill it in
```

On first start, each Mineflayer bot prints a Microsoft device-code login. Sign in once and the token is cached.

### Run

Start each process in its own terminal or service:

```bash
python bot/main.py       # Discord bot, Minecraft bots, IPC API
python bot/web_main.py   # Web panel on PANEL_PORT (default 8080)
```

For frontend work, `npm --prefix frontend run dev` starts Vite on port 5173 and proxies `/api` to the panel. After `npm run build`, restart `web_main.py`, because it caches `index.html` at startup.

To test against real data, [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) explains how to copy the production database locally.

## Configuration

Secrets and Discord IDs live in `.env` (see [example.env](example.env) for the full list). The main ones:

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Discord bot token |
| `HYPIXEL_API_KEY` | Hypixel API key, limited to 300 requests per 5 minutes and shared by every feature |
| `DATABASE_URL` | PostgreSQL connection string |
| `KINDERGARTEN_USERNAME` / `UNIVERSITY_USERNAME` | Microsoft accounts for the Minecraft bots |
| `MINECRAFT_VERSION` | Protocol version the bots connect with: `26.1` to sit in SkyBlock (needed for `.warpout`), default `1.8.9`. Bots fall back to 1.8.9 on their own if 26.1 keeps disconnecting |
| `BRIDGE_CHANNEL` / `OFFICER_CHANNEL` | Webhook URLs for the bridge channels |
| `*_STAFF_ROLE_ID`, `EXEC_ROLE_ID` | Roles that gate slash commands |
| `PANEL_DISCORD_CLIENT_ID` / `_SECRET` / `PANEL_REDIRECT_URI` | Discord OAuth2 app for panel login |
| `PANEL_JWT_SECRET`, `BOT_IPC_SECRET` | Random secrets: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `PANEL_ADMIN_DISCORD_ID` | Panel owner, made an admin on first login |

Gameplay settings that change often (rank requirements, inactivity thresholds, activity tiers) are edited on the panel's **Config** page and take effect within about 20 seconds, with no restart.

## Deployment

Every push to `master` triggers a [GitHub Action](.github/workflows/deploy.yml) that SSHes into the VPS and runs [deploy.sh](deploy.sh). The script pulls, installs dependencies and rebuilds the frontend only for the parts that changed, runs migrations, then restarts both processes under pm2 (`bumble-bot`, `bumble-web`).
