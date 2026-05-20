# Bumble Bot — Project Reference

This file is the authoritative guide for working on this codebase. Keep it updated whenever you add files, rename things, change architecture, or add new guilds.

---

## Project Purpose

Bumble is a Discord bot that acts as a bridge between two Hypixel Skyblock Minecraft guilds — **Bumble Kindergarten (BK)** and **Bumble University (BU)** — and their shared Discord server. It:

- Relays chat between Minecraft guild chat ↔ Discord (both directions)
- Cross-relays chat between the two guilds in-game (`[BK] player: message` appears in BU and vice versa)
- Provides in-game dot-commands (`.lvl`, `.cata`, `.nw`, etc.) that query the Hypixel API
- Exposes Discord slash commands for staff to manage guild members (invite, kick, mute, promote, demote)
- Tracks armor dye drops per player and assigns Discord color roles
- Links Discord accounts to Minecraft UUIDs via Hypixel social media verification
- Manages guild application ticket channels

---

## Folder Structure

```
bumble-unified/
├── main.py                   # Entry point — Discord client, GuildState, cog loading
├── config.py                 # All configuration + GuildConfig dataclass + BK/BU instances
├── constants.py              # Static lookup tables: dungeon XP, MP values, dye IDs/roles/emojis
├── requirements.txt          # Python dependencies
├── package.json              # Node.js dependencies (Mineflayer, skyhelper-networth)
├── example.env               # Template for .env — copy and fill before running
│
├── db/
│   ├── __init__.py           # Exports `manager` singleton (DatabaseManager instance)
│   └── manager.py            # DatabaseManager — all SQLite access goes through here
│
├── lib/                      # Low-level utility functions (no Discord, no cog state)
│   ├── __init__.py           # Re-exports all lib symbols
│   ├── condense.py           # Number formatter: 1_500_000 → "1.5M"
│   ├── deep_get.py           # Safe nested dict access
│   ├── fetch.py              # async fetch() and sync request() for HTTP/JSON
│   ├── get_username.py       # UUID → IGN, with DB cache
│   ├── get_uuid.py           # IGN → UUID, with DB cache
│   └── rankup.py             # guild_rank_change() — promotes/demotes a player in-game
│
├── player/                   # Hypixel Skyblock player data classes
│   ├── __init__.py           # Exports Player
│   ├── skyblock.py           # Player — top-level class, fetches all profiles
│   ├── level.py              # SkyblockLevel — current and highest level across profiles
│   ├── catacombs.py          # Catacombs — level, secrets, S/R, PB times
│   ├── slayers.py            # Slayers — claimed levels for all 6 boss types
│   ├── magical_power.py      # MagicalPower — decodes talisman bag NBT, calculates MP
│   └── networth.py           # Networth — delegates to skyhelper-networth JS library
│
├── utils/
│   ├── command_handler.py    # bridge_commands() — routes .commands from Minecraft/Discord
│   └── roll_dye.py           # roll_dye() — weighted random dye drop, announces if new
│
├── web/                      # FastAPI web panel backend
│   ├── app.py                # create_app() factory — mounts routes, auth, WebSocket, SPA fallback
│   ├── auth.py               # Discord OAuth2 exchange, JWT create/verify, FastAPI dependencies
│   ├── logs.py               # LogBroadcaster (thread-safe store) + WebLogHandler (logging.Handler)
│   └── routes/
│       ├── bots.py           # GET /api/bots, POST /api/bots/{key}/restart|stop
│       └── users.py          # CRUD /api/users — panel user management (admin only)
│
├── frontend/                 # React/Vite web panel frontend
│   ├── index.html            # SPA entry point
│   ├── package.json          # Frontend dependencies (React, React Router, Vite)
│   ├── vite.config.ts        # Vite config — proxies /api and /ws to backend in dev
│   ├── tsconfig.json
│   ├── dist/                 # Built output — served by FastAPI as static files
│   └── src/
│       ├── main.tsx          # React root
│       ├── App.tsx           # Auth context, routing, sidebar Layout
│       ├── api.ts            # Typed fetch wrappers for all API endpoints + wsLogsUrl()
│       ├── types.ts          # Shared TypeScript interfaces (Me, Bot, PanelUser, LogRecord)
│       ├── index.css         # Dark theme CSS — variables, layout, cards, buttons, log viewer
│       └── pages/
│           ├── Login.tsx     # Discord OAuth login page
│           ├── Dashboard.tsx # Bot status cards with start/stop/restart controls
│           ├── Logs.tsx      # Live log stream (WebSocket) with level filter + search
│           └── Users.tsx     # Panel user management table with add/edit/delete modal
│
└── cogs/
    ├── errors/
    │   └── error_handler.py  # Global slash command error handler (MissingRole, Cooldown, etc.)
    │
    ├── commands/             # Discord slash command cogs
    │   ├── guild_commands.py # /bk-guild and /bu-guild command groups (list, mute, kick, etc.)
    │   ├── link.py           # /link — self-serve Discord ↔ Minecraft account linking
    │   ├── staff.py          # /staff link — staff-forced account linking
    │   ├── user.py           # /user — look up a linked account (staff only)
    │   ├── admin.py          # /admin add-dye, remove-dye (exec role only)
    │   ├── dyes.py           # /dyes — select a dye role from owned dyes
    │   ├── apply.py          # /apply — create a private application ticket channel
    │   └── exec.py           # /bk-exec, /bu-exec — run raw MC commands (exec role only)
    │
    └── bridge/               # One set of cogs handles both guilds via GuildConfig
        ├── bridge.py         # GuildBridge — MC→Discord chat relay + Discord→MC listener
        ├── connections.py    # GuildConnections — spawn/disconnect events, auto-reconnect
        └── message_handler.py# GuildMessageHandler — system messages (join/leave/kick/mute/invite)
```

---

## Key Files and Their Responsibilities

### `main.py`
- Defines `GuildState` dataclass: holds the live Mineflayer bot instance, guild list buffer, invite result buffer, and logs webhook for one guild.
- Defines `Client(commands.Bot)`: holds `guild_configs` (static config map) and `guilds_state` (runtime state map, both keyed `'bk'`/`'bu'`), shared webhooks, and the skyhelper JS reference.
- `setup_hook()` runs on startup: creates Mineflayer bots, sets per-guild log webhooks, sets shared webhooks, then dynamically loads every `.py` file inside every `cogs/` subdirectory.
- `start_mineflayer()` is also called on reconnect (via `connections.py`) with `restart=True` to reload bridge cogs against the new bot instance.

### `config.py`
- Loads all env vars and defines every scalar config constant the rest of the code imports.
- Defines `GuildConfig` dataclass — the single source of truth for per-guild settings:
  - `key` (`'bk'`/`'bu'`) — used as dict key everywhere
  - `mc_options` — passed directly to `mineflayer.createBot()`
  - `guild_name` — matched against `/guild list` output to accumulate the list
  - `staff_role_id`, `member_role_id` — Discord role IDs for permission checks
  - `ranks` — `{bot_rank_key: skyblock_level_requirement}` for auto-rankup
  - `rank_update_users` — IGNs authorized to run `.ranks`
  - `discord_rank_map` — maps Hypixel guild rank names to bot rank keys for bulk `.ranks`
  - `bridge_channel_id` / `officer_channel_id` — which Discord channels feed into this guild's MC chat (`None` = no Discord→MC listener for that guild)
- `GUILD_CONFIGS: dict[str, GuildConfig]` — the master registry. **Adding a new guild = adding one entry here.**
- Backward-compatible flat constants (`BK_STAFF_ROLE`, `BRIDGE_CHANNEL_ID`, etc.) are still exported for cogs that reference them directly.

### `db/manager.py`
- `DatabaseManager` provides typed methods for every DB operation so raw SQL is never written inline in cogs.
- All connections enable `PRAGMA foreign_keys = ON` via the `connection()` context manager.
- Key methods: `get_ign()`, `get_uuid_by_discord()`, `get_user_by_discord()`, `get_user_by_ign()`, `link_user()`, `is_linked()`, `get_unlocked_dyes()`, `get_all_dyes_weighted()`, `mark_dye_received()`, `add_dye()`, `remove_dye()`.
- `db/__init__.py` exports a module-level `manager` singleton — cogs do `from db import manager`.
- `lib/get_uuid.py` and `lib/get_username.py` use `sqlite3` directly (not `DatabaseManager`) because they are synchronous low-level utilities called from non-cog contexts.

### `cogs/bridge/bridge.py`
- `GuildBridge` is instantiated once per guild by its `setup()`. Each instance registers a Mineflayer `On(state.bot, "chat")` handler scoped to that guild's bot.
- **MC → Discord**: parses rank/player/message from guild chat, sends to the shared bridge or officer webhook, logs to message_logs, then relays to all *other* guild bots with a `[BK]`/`[BU]` prefix.
- **Discord → MC**: only active when `config.bridge_channel_id` is not `None` (currently only BK). Resolves the author's IGN from DB, formats the message (handling replies), and sends to every guild bot.
- `.commands` in Minecraft chat are routed to `bridge_commands()` via `run_coroutine_threadsafe` (Mineflayer callbacks run in a thread, not the asyncio event loop).

### `cogs/bridge/message_handler.py`
- Listens to `messagestr` (raw text lines from Minecraft, not parsed chat).
- Accumulates `/guild list` and `/guild online` output into `state.guild_list` (used by `/bk-guild list` slash command).
- Detects system events (join, leave, kick, mute, unmute, promote, demote, invite result, join request) and sends embeds to bridge/officer/logs webhooks.
- For join requests, fetches the applicant's Skyblock level via `skyblock.Player` and includes it in the embed.

### `utils/command_handler.py`
- `bridge_commands(client, message, username, guild_rank, chat_state, config)` dispatches `.help`, `.lvl`, `.hlvl`, `.nw`, `.slayer`, `.cata`, `.pb`, `.mp`, `.bank`, `.chim`, `.ranks`.
- Each handler is a private `async` function that returns `(display_name, response_text, raw_username)`. The dispatcher sends the response to all guild bots and the appropriate webhook.
- `.ranks` uses `config.rank_update_users` to authorize, `config.discord_rank_map` to translate Hypixel rank names, and `config.ranks` + `guild_rank_change()` to do the actual promotions/demotions.

### `cogs/commands/guild_commands.py`
- Contains `BKGuild` and `BUGuild` as two `GroupCog` classes in one file. Shared helper `_guild_list_embed()` avoids duplication.
- Each class reads from `client.guilds_state['bk']` or `['bu']` rather than `client.bk_bot` directly.
- **To add a third guild:** add a new `GroupCog` subclass here and a line in `setup()`.

### `web/app.py`
- `create_app(client)` receives the live `Client` instance and stores it as `app.state.client` so routes can access it.
- Mounts `web/routes/bots.py` and `web/routes/users.py` as routers.
- Handles Discord OAuth2 callback: exchanges code for a Discord user object, auto-provisions the admin user on first login, issues a JWT, redirects to `/?token=...`.
- Serves `GET /api/me` (returns JWT claims as JSON) and `WS /ws/logs` (streams log records from `LogBroadcaster`).
- If `frontend/dist/` exists, mounts `/assets` as static files and serves `index.html` for all other routes (SPA fallback). The HTML is **read at startup and cached**; restart the server after a frontend rebuild or it will serve a stale `index.html` referencing the old JS bundle.

### `web/auth.py`
- `discord_oauth_url()` builds the Discord OAuth2 authorization URL.
- `exchange_code(code)` exchanges the authorization code for the user's Discord profile dict via aiohttp.
- `create_token()` / `verify_token()` — HS256 JWT, 24-hour expiry. Payload keys: `sub` (discord_id str), `name`, `admin` (bool), `logs` (bool), `avatar` (URL str).
- FastAPI dependencies: `require_auth`, `require_admin`, `require_logs` — all read `Authorization: Bearer <token>` and raise `HTTPException` on failure.

### `web/logs.py`
- `LogBroadcaster` — thread-safe list protected by `threading.Lock`. `broadcast()` appends and trims to `MAX_HISTORY=500`. `snapshot()` returns full copy; `get_after(offset)` returns records from offset onward.
- `WebLogHandler(logging.Handler)` — attached to the root logger at startup (`main.py`). `emit()` calls `broadcaster.broadcast()` directly (no asyncio, no queue). This is the only correct approach: the log handler runs in arbitrary threads; the broadcaster uses a plain `Lock` so it's safe from any thread.
- The WebSocket in `app.py` sends the full history on connect, then polls `get_after(sent)` every 200ms.

### `web/routes/bots.py`
- `GET /api/bots` — returns `{key: {key, name, short_name, username, connected}}` for all guilds. `connected` is derived from `not getattr(state.bot, "ended", True)`.
- `POST /api/bots/{key}/restart` — calls `await client.start_mineflayer(restart=True, account=key)`.
- `POST /api/bots/{key}/stop` — sets `state.manual_stop = True`, then calls `state.bot.end()`. The `manual_stop` flag prevents `connections.py` from auto-reconnecting.

### `web/routes/users.py`
- CRUD for the `panel_users` table: list, create, update permissions, delete.
- All endpoints require admin. Self-demotion and self-deletion are blocked.

### `frontend/src/App.tsx`
- `AuthProvider` — reads `?token=` from URL on mount (OAuth redirect), stores in `localStorage`, fetches `/api/me`, exposes `{me, loading, logout}` context.
- `Layout` — sidebar with nav links (Dashboard always visible; Logs if admin or can_view_logs; Users if admin), Discord avatar + username, Logout button.
- `AppRouter` — unauthenticated users see `Login`; authenticated users see `Layout` with nested routes.

### `frontend/src/pages/Dashboard.tsx`
- Polls `/api/bots` every 10s. Each bot card shows name, MC username, online/offline status dot, and Start/Stop + Restart buttons.
- Stop/Start are mutually exclusive based on `bot.connected`. Stop optimistically sets `connected: false` in local state immediately after the API call succeeds. Restart polls after 3s to pick up the new connection.

### `frontend/src/pages/Logs.tsx`
- Connects to `WS /ws/logs?token=<jwt>`. Auto-reconnects after 3s on disconnect.
- Renders each record as a log line with timestamp, source file, level badge, and message. Supports level filter and text search. Pin-to-bottom toggle.

### `frontend/src/pages/Users.tsx`
- Table of all panel users with add/edit/delete. Add and edit use the same modal with discord_id, display name, is_admin, can_view_logs fields.

---

## Dependencies

### Python (`requirements.txt`)
| Package | Why |
|---------|-----|
| `discord.py >= 2.6.4` | Discord bot framework — slash commands, webhooks, events |
| `javascript >= 1!1.2.6` | Bridges Python ↔ Node.js; lets Python call Mineflayer and skyhelper |
| `python-dotenv` | Loads `.env` file into `os.environ` |
| `aiohttp` | Async HTTP for `lib/fetch.py` and Discord OAuth2 token exchange |
| `requests` | Sync HTTP for `lib/fetch.py` (used in synchronous player data fetches) |
| `emoji` | Converts Discord emoji to text (`:bee:`) before sending to Minecraft |
| `NBT` | Decodes base64-encoded NBT data from talisman bags (magical power calc) |
| `fastapi >= 0.115.0` | Web panel API framework |
| `uvicorn >= 0.32.0` | ASGI server — runs FastAPI alongside the Discord bot via `asyncio.gather` |
| `websockets >= 13.0` | WebSocket support for the live log stream endpoint |
| `PyJWT >= 2.10.0` | JWT creation and verification for stateless panel sessions |
| `pydantic >= 2.0.0` | Request body validation for FastAPI routes |

### Node.js (`package.json`)
| Package | Why |
|---------|-----|
| `mineflayer` | Minecraft bot client — connects to Hypixel, sends/receives chat |
| `skyhelper-networth` | Calculates player net worth from profile data; called via the `javascript` bridge |

### Frontend (`frontend/package.json`)
| Package | Why |
|---------|-----|
| `react` / `react-dom` | UI framework |
| `react-router-dom` | Client-side routing (Dashboard, Logs, Users) |
| `vite` | Build tool; also runs a dev server that proxies `/api` and `/ws` to the Python backend |
| `typescript` | Type safety across all frontend code |

---

## Architecture: How the Pieces Connect

```
Discord Server
    │
    │  webhooks (SyncWebhook)         slash commands (app_commands)
    ▼                                         ▼
Client (main.py)  ◄────────────────  cogs/commands/*.py
    │                                         │
    │  guilds_state['bk'].bot                 │  db/manager.py (DatabaseManager)
    │  guilds_state['bu'].bot                 │
    ▼                                         ▼
Mineflayer bots (JS/Node.js)          bumble.db (SQLite3)
    │
    │  On("chat") / On("messagestr")
    ▼
cogs/bridge/bridge.py        →  utils/command_handler.py  →  player/*.py  →  Hypixel API
cogs/bridge/message_handler.py
cogs/bridge/connections.py
```

**Request path for an in-game `.lvl` command:**
1. Mineflayer fires `chat` event on `guilds_state['bk'].bot`
2. `GuildBridge.handle_minecraft_message()` detects message starts with `.`
3. `run_coroutine_threadsafe(bridge_commands(..., config=BK_CONFIG), client.loop)` schedules the coroutine
4. `bridge_commands()` calls `_skyblock_level()` which constructs `skyblock.Player(username=...)`
5. `Player.__init__` calls `get_uuid()` (DB cache → Mojang API) then `request()` to Hypixel profiles API
6. Response is sent to all guild bots via `state.bot.chat()` and to the webhook

**Request path for a Discord bridge message:**
1. `GuildBridge.on_message()` fires (only BK bridge, since BU has `bridge_channel_id=None`)
2. IGN resolved via `manager.get_ign(discord_id)`
3. Content formatted (emoji demojized, reply chain resolved)
4. Sent to `guilds_state['bk'].bot.chat()` and `guilds_state['bu'].bot.chat()` simultaneously

---

## Data Flow

### Minecraft → Discord
```
Mineflayer "chat" event
  → GuildBridge parses rank/player/message via regex
  → Sends to bridge or officer SyncWebhook
  → Relays to all other guild bots with [BK]/[BU] prefix
  → If message starts with ".", dispatches to bridge_commands()
```

### Discord → Minecraft
```
on_message (only BK bridge channel / officer channel)
  → Resolve IGN from DB (fallback to display name)
  → Format: "IGN: message" or "IGN ➜ ReplyIGN: message"
  → Send to ALL guilds_state[*].bot.chat()
```

### System messages (join/leave/kick/etc.)
```
Mineflayer "messagestr" event
  → GuildMessageHandler matches known phrases
  → Sends embed to bridge + officer + per-guild logs webhook
```

### Auto-reconnect
```
Mineflayer "end" event
  → GuildConnections sends disconnect embed
  → asyncio.sleep(5) then client.start_mineflayer(restart=True, account=config.key)
  → Reloads bridge extension modules against the new bot instance
```

---

## Database Schema

Three tables in `bumble.db` (SQLite3):

```sql
CREATE TABLE users (
    uuid         TEXT PRIMARY KEY,
    ign          TEXT,
    discord_id   INTEGER,      -- NULL until linked
    discord_name TEXT          -- NULL until linked
);

CREATE TABLE dyes (
    dye_id   TEXT PRIMARY KEY,
    dye_name TEXT,
    weight   REAL,             -- higher weight = more common drop
    hex      TEXT              -- color hex for embed, e.g. "FF3C3C"
);

CREATE TABLE users_dyes (
    uuid     TEXT REFERENCES users(uuid),
    dye_id   TEXT REFERENCES dyes(dye_id),
    received INTEGER DEFAULT 0  -- 0 = not yet received, 1 = received
);
```

`PRAGMA foreign_keys = ON` is set on every connection via `DatabaseManager.connection()`.

UUID resolution (`get_uuid` / `get_username`) always writes to `users` as a side effect, so `users` doubles as a UUID↔IGN cache even for players who never link their Discord.

---

## Patterns and Conventions

### Per-guild branching via GuildConfig
Never write `if guild == 'bk': ... elif guild == 'bu': ...`. Instead, pass or access `GuildConfig` and read its attributes. This keeps all guild-specific data in `config.py` where it belongs.

### Cog naming for multi-instance cogs
Bridge cogs are loaded once (one `setup()` call) but each creates multiple instances — one per guild. Instance names are set via `self.__cog_name__ = f"{config.key}_bridge"` before `super().__init__()` so Discord.py tracks them under unique names.

### Thread safety in Mineflayer callbacks
Mineflayer `On()`/`Once()` callbacks run in a background thread managed by the `javascript` bridge, not in the asyncio event loop. Never `await` inside them. To call async code, use:
```python
run_coroutine_threadsafe(some_coroutine(...), self.client.loop)
```

### Synchronous vs async HTTP
- `lib/fetch.py::fetch()` — async, use inside `async def` (Discord cogs, bridge_commands)
- `lib/fetch.py::request()` — synchronous, use inside Mineflayer callbacks or `Player.__init__` (which runs synchronously during profile fetch)

### DatabaseManager usage
All cog-level DB access goes through `from db import manager` and calls its typed methods. Raw `sqlite3.connect()` is only acceptable inside `lib/get_uuid.py` and `lib/get_username.py` (low-level cache utilities predating the manager).

### Webhook vs interaction response
- Bridge messages use `SyncWebhook.send()` (synchronous, called from threads or sync contexts)
- Slash command responses use `await interaction.response.send_message()` or `await interaction.edit_original_response()` after `defer()`

### Deferred interactions
Any slash command that does I/O (DB, Hypixel API, `asyncio.sleep`) must call `await interaction.response.defer()` first, then `await interaction.edit_original_response(embed=embed)` when done. Commands that are instant (mute, unmute, kick) can use `send_message()` directly.

---

## Things to Watch Out For

### The `javascript` bridge is threaded
All Mineflayer event handlers (`@On`, `@Once`) run in their own thread. Accessing `client` attributes from inside them is safe for reads, but any mutation of shared state (like `state.guild_list`) must be treated carefully. Currently the only writes are appends to lists and simple flag assignments, which is safe enough in CPython due to the GIL.

### Reconnect reloads bridge extensions
`start_mineflayer(restart=True)` calls `reload_extension("cogs.bridge.*")` for all three bridge modules. This re-runs their `setup()` functions, which create new cog instances with fresh Mineflayer event bindings. Old bindings on the dead bot instance are abandoned. If you add new bridge modules, add their reload call to `start_mineflayer()`.

### `asyncio.run()` inside Mineflayer callbacks
`connections.py` uses `asyncio.run(reconnect())` inside the `end` handler. This creates a new event loop in the callback thread specifically for the reconnect sleep + restart sequence. It works but is fragile — if the reconnect itself errors, the exception is swallowed by the thread. This matches the original design and is flagged as a known rough edge.

### Guild list race condition
`/bk-guild list` sends `/guild list` to Minecraft, sets `state.save_guild_list = True`, sleeps 0.75s, then reads `state.guild_list`. If two people run the command simultaneously, the lists will get interleaved. The 0.75s sleep is a best-effort wait, not a proper lock. Don't add concurrent guild list features without addressing this.

### `skyblock.Player` is synchronous and slow
`Player.__init__` makes multiple blocking HTTP requests (Mojang UUID lookup, Hypixel profiles). It should never be constructed inside a Mineflayer callback directly — always schedule it via `run_coroutine_threadsafe` and use an async wrapper. Bridge commands already do this correctly.

### Frontend rebuild requires server restart
`web/app.py` reads `frontend/dist/index.html` once at startup and caches it in memory. After running `npm run build`, the new JS bundle gets a new filename hash. If the server is not restarted it will keep serving the old `index.html`, which references the missing old bundle — the browser loads a blank page. Always restart the Python process after a frontend rebuild.

### panel_users is a separate DB table from users
The `panel_users` table (created by `manager.setup_panel_tables()`) holds web panel access control and is completely separate from the `users` table (which stores Discord↔Minecraft links). A user can exist in `users` without being in `panel_users` and vice versa. The first login by `PANEL_ADMIN_DISCORD_ID` auto-creates their `panel_users` row if it doesn't exist yet.

### JWT permissions are baked in at login time
The JWT encodes `admin` and `logs` permissions at the moment of login and is valid for 24 hours. If an admin changes a user's permissions in the Users panel, the change takes effect only after that user's token expires and they log in again. There is no token revocation mechanism.

### NBT parsing monkey-patch
`player/magical_power.py` monkey-patches `nbt.nbt.TAG_String._parse_buffer` to handle non-UTF-8 strings in talisman NBT data. This runs at import time. It is a workaround for malformed Minecraft item names and must not be removed.

### BU bridge has no Discord → Minecraft listener
`BU_CONFIG.bridge_channel_id = None` intentionally. All Discord messages go through the BK bridge's `on_message`, which sends to all bots. BU bridge only handles MC → Discord direction. If you need BU to have its own Discord input channel, set `BU_CONFIG.bridge_channel_id` and `BU_CONFIG.officer_channel_id` and add the corresponding env vars.

### Adding a new guild
1. Add env vars for the new MC account, webhook URLs, role IDs, and rank requirements to `.env` and `example.env`
2. Load them in `config.py` and create a new `GuildConfig` instance
3. Add it to `GUILD_CONFIGS`
4. Add its log webhook URL to `log_urls` in `main.py`
5. Add a new `XGuild(commands.GroupCog, name="x-guild")` class in `guild_commands.py` and register it in `setup()`
6. Everything else (bridge relay, `.ranks`, reconnect) picks up the new guild automatically

---

## Environment Variables

See `example.env` for the full list. Critical ones:

| Variable | Used by |
|----------|---------|
| `DISCORD_BOT_TOKEN` | `config.py` → `main.py` login |
| `HYPIXEL_API_KEY` | All Hypixel API requests in `lib/` and `player/` |
| `KINDERGARTEN_USERNAME` / `UNIVERSITY_USERNAME` | Mineflayer login; also used to filter the bot's own messages |
| `KINDERGARTEN_BRIDGE_CHANNEL` (webhook URL) | `client.bridge` SyncWebhook |
| `KINDERGARTEN_BRIDGE_CHANNEL_ID` (channel ID) | `GuildBridge.on_message` filter |
| `BK_STAFF_ROLE_ID` / `BU_STAFF_ROLE_ID` | Slash command permission checks |
| `EXEC_ROLE_ID` | `/admin` and `/bk-exec`/`/bu-exec` permission checks |
| `PANEL_PORT` | Port uvicorn listens on (default 8000) |
| `PANEL_DISCORD_CLIENT_ID` | Discord OAuth2 app client ID (`web/auth.py`) |
| `PANEL_DISCORD_CLIENT_SECRET` | Discord OAuth2 app client secret (`web/auth.py`) |
| `PANEL_REDIRECT_URI` | OAuth2 redirect URI, e.g. `https://bumble.seazyns.dev/auth/callback` |
| `PANEL_JWT_SECRET` | Random secret for signing JWTs — keep private |
| `PANEL_ADMIN_DISCORD_ID` | Discord ID of the panel owner; auto-provisioned as admin on first login |
