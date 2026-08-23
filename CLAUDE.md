# Bumble Bridge Bot — Project Reference

This file is the authoritative guide for working on this codebase. Keep it updated whenever you add files, rename things, change architecture, or add new guilds.

---

## Project Purpose

Bumble is a Discord bot that acts as a bridge between two Hypixel Skyblock Minecraft guilds — **Bumble Kindergarten (BK)** and **Bumble University (BU)** — and their shared Discord server. It:

- Relays chat between Minecraft guild chat ↔ Discord (both directions)
- Cross-relays chat between the two guilds in-game (`[BK] player: message` appears in BU and vice versa)
- Provides in-game dot-commands (`.lvl`, `.cata`, `.nw`, etc.) that query the Hypixel API
- Exposes Discord slash commands for staff to manage guild members (invite, kick, mute, promote, demote)
- Continuously refreshes guild member Skyblock stats in the background and auto-promotes/demotes members by level
- Tracks armor dye drops per player and assigns Discord color roles
- Links Discord accounts to Minecraft UUIDs via Hypixel social media verification
- Manages guild application ticket channels
- Exposes a web panel (React + FastAPI) for bot control, guild member/leaderboard browsing, and live log streaming

---

## Process Architecture

The bot and the web panel are **two separate OS processes**, each with their own `asyncio` event loop, that never share Python objects. They coordinate only through:
1. **PostgreSQL** — the source of truth for members, links, dyes, message counts, etc.
2. **An internal HTTP IPC API** — the web process calls the bot process over `localhost` to read live state (connection status, recent chat) or trigger actions (restart/stop a Mineflayer bot).

```
bot/main.py            bot/web_main.py
   (bot process)           (web process)
   Discord client          FastAPI panel
   + Mineflayer bots       + serves frontend/dist
   + bot_ipc.py FastAPI    + calls bot IPC over HTTP
     on 127.0.0.1:BOT_IPC_PORT
        ▲                       │
        └────── X-IPC-Secret ───┘
                (BOT_IPC_URL)

Both processes independently run `db.migrate.run_migrations()` on startup
and both talk directly to PostgreSQL via `db/manager.py`.
```

Run them as two separate commands/services in production (see `deploy.sh`):
```bash
python bot/main.py       # Discord bot + Mineflayer + internal IPC API
python bot/web_main.py   # Web panel (talks to the bot process via IPC)
```

---

## Folder Structure

```
bumble-unified/
├── deploy.sh                 # VPS deploy script
├── example.env               # Template for .env — copy and fill before running
│
├── docs/                      # All project documentation other than this file
│   ├── README.md               # Project overview, features, setup, architecture
│   └── DEVELOPMENT.md          # Prod DB copy script usage
│
├── frontend/                 # React/Vite web panel UI
│   └── src/
│       └── ...
│
└── bot/                      # All Python + Node bot code
    ├── main.py               # Bot process entry point — Discord client, GuildState, Mineflayer, IPC server
    ├── web_main.py           # Web panel process entry point — runs migrations, serves FastAPI panel
    ├── bot_ipc.py            # create_ipc_app(client) — internal FastAPI app exposed only on localhost
    ├── config.py             # All configuration + GuildConfig dataclass + BK/BU instances
    ├── constants.py          # Static lookup tables: dungeon XP, dungeon floor XP + class boosts, MP values, dye IDs/roles/emojis
    ├── requirements.txt      # Python dependencies
    ├── package.json          # Node.js dependencies (Mineflayer, skyhelper-networth)
    │
    ├── db/
    │   ├── __init__.py       # Exports `manager` singleton (DatabaseManager instance), reads DATABASE_URL
    │   ├── base.py           # BaseQueries — shared connection pool + _cursor() contextmanager, inherited by every mixin below
    │   ├── manager.py        # DatabaseManager — composes the query mixins below; all PostgreSQL access goes through `from db import manager`
    │   ├── queries/          # One mixin per domain, each inheriting BaseQueries; DatabaseManager multiply-inherits all of them
    │   │   ├── users.py        # UsersQueries — Discord<->MC links (`users` table), incl. link_user/unlink_user
    │   │   ├── dyes.py         # DyesQueries — dye catalog + per-player unlocks (`dyes`/`users_dyes`)
    │   │   ├── guild_members.py# GuildMembersQueries — roster + stats (`guild_members`)
    │   │   ├── panel_users.py  # PanelUsersQueries — web panel access control (`panel_users`)
    │   │   ├── api_usage.py    # ApiUsageQueries — Hypixel call logging (`api_calls`)
    │   │   └── message_counts.py # MessageCountsQueries — per-player message counts/leaderboard (`message_counts`)
    │   ├── migrate.py        # run_migrations(dsn) — applies db/migrations/*.sql in order, tracked in schema_migrations
    │   └── migrations/       # Numbered SQL migration files (001_initial_schema.sql, 002_panel_users.sql, ...)
    │
    ├── lib/                  # Low-level utility functions (no Discord, no cog state)
    │   ├── __init__.py       # Re-exports all lib symbols
    │   ├── condense.py       # Number formatter: 1_500_000 → "1.5M"
    │   ├── deep_get.py       # Safe nested dict access
    │   ├── fetch.py          # async fetch() and sync request() for HTTP/JSON
    │   ├── get_username.py   # UUID → IGN, with DB cache
    │   ├── get_uuid.py       # IGN → UUID, with DB cache
    │   ├── guild_list.py     # parse_guild_list() / parse_online_igns() — parses raw /guild list & /guild online text
    │   ├── hypixel.py        # fetch_member_stats() / fetch_mayor_multiplier() / fetch_key_info() — Hypixel player+key lookups, records api_calls
    │   └── rankup.py         # guild_rank_change() — promotes/demotes a player in-game
    │
    ├── player/               # Hypixel Skyblock player data classes
    │   ├── __init__.py       # Exports Player
    │   ├── skyblock.py       # Player — top-level class, fetches all profiles
    │   ├── level.py          # SkyblockLevel — current and highest level across profiles
    │   ├── catacombs.py      # Catacombs — level, secrets, S/R, PB times
    │   ├── class_average.py  # ClassAverage — class XP, XP boosts, runs remaining to a class average
    │   ├── slayers.py        # Slayers — claimed levels for all 6 boss types
    │   ├── magical_power.py  # MagicalPower — decodes talisman bag NBT, calculates MP
    │   └── networth.py       # Networth — delegates to skyhelper-networth JS library
    │
    ├── utils/
    │   ├── command_handler.py # bridge_commands() — routes .commands from Minecraft/Discord
    │   └── roll_dye.py        # roll_dye() — weighted random dye drop, announces if new
    │
    ├── web/                  # FastAPI web panel backend
    │   ├── app.py             # create_app() factory — mounts routers, OAuth2, /api/me, SPA fallback
    │   ├── auth.py             # Discord OAuth2 exchange, JWT create/verify, FastAPI permission dependencies
    │   └── routes/
    │       ├── bots.py         # /api/bots/* — bot status, guild overview/members/leaderboard, link mgmt, IPC proxy
    │       ├── users.py        # CRUD /api/users — panel user management (admin only)
    │       └── dyes.py         # /api/dyes/* — own/other players' dye profiles, search, recent drops
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
        ├── bridge/               # One set of cogs handles both guilds via GuildConfig
        │   ├── bridge.py         # GuildBridge — MC→Discord chat relay + Discord→MC listener
        │   ├── connections.py    # GuildConnections — spawn/disconnect events, auto-reconnect, Hypixel member sync
        │   └── message_handler.py# GuildMessageHandler — system messages (join/leave/kick/mute/invite), auto-rank on join
        │
        └── tasks/
            └── member_refresh.py # MemberRefreshTask — background loop that continuously refreshes one member's
                                   # stats at a time and auto-ranks them (see "Background member refresh" below)
```

---

## Key Files and Their Responsibilities

### `bot/main.py`
- Defines `GuildState` dataclass: holds the live Mineflayer bot instance, `connected` flag, guild-list/guild-online buffers, invite result buffer, per-guild logs webhook, `manual_stop` flag, `guild_member_count`, and a `recent_chat` deque (last 50 messages, used by the web panel's guild overview).
- Defines `Client(commands.Bot)`: holds `guild_configs` (static config map) and `guilds_state` (runtime state map, both keyed `'bk'`/`'bu'`), shared webhooks, and the skyhelper JS reference.
- `setup_hook()` runs on startup: creates Mineflayer bots, sets per-guild log webhooks, sets shared webhooks, then dynamically loads every `.py` file inside every `cogs/` subdirectory (including `cogs/tasks/`).
- `start_mineflayer()` only creates the raw Mineflayer bot object(s); it no longer knows about cog reloading. On reconnect (via `connections.py`) or a manual restart (via `bot_ipc.py`), the caller follows it with `cogs.bridge.connections.reload_bridge_cogs(client, config)` to reload the `connections`, `bridge`, and `message_handler` cogs against the new bot instance — see `cogs/bridge/connections.py` below.
- `run_bot()` applies DB migrations, then runs the Discord client and the internal `bot_ipc` FastAPI server concurrently via `asyncio.gather`.
- Right after `mineflayer = require("mineflayer")`, module-level code patches `minecraft-data`'s cached protocol object for `VERSION` so Hypixel's `window_items` packet is read as an opaque `restBuffer` instead of being structurally parsed. Works around an open upstream mineflayer/protodef bug where Minecraft 1.20.5+'s "Data Components" item encoding desyncs the NBT parser on that packet specifically (`Invalid tag: N > 20` in `play.toClient`, crashing a few seconds after spawn — see PrismarineJS/mineflayer #3669/#3787/#3583/#3750). Confirmed via `bot/scripts/test_mineflayer.py` that mineflayer's own `inventory.js` handler for this packet degrades to a silent no-op on an unparsed body rather than crashing, and that the patch is harmless on the `1.8.9` default too — so it's applied unconditionally rather than gated on `VERSION`. The one cost: `bot.inventory`/hotbar tracking won't reflect real contents, which nothing in this codebase reads anyway. Set `MINECRAFT_VERSION=1.8.9` in `.env` to fall back to the always-stable legacy path if a newer version misbehaves in some other way.

### `bot/web_main.py`
- Separate process entry point for the web panel. Applies DB migrations, then serves `web/app.py`'s FastAPI app with uvicorn on `PANEL_PORT`.
- Does **not** hold a `Client` instance — all bot state is read through the IPC API in `web/routes/bots.py`.

### `bot/bot_ipc.py`
- `create_ipc_app(client)` builds a FastAPI app that runs only inside the bot process, bound to `127.0.0.1:BOT_IPC_PORT`.
- Every route requires the `X-IPC-Secret` header (via `_verify`) to match `BOT_IPC_SECRET` when that env var is set.
- Routes: `GET /status` (per-guild connection status), `GET /guild/{key}/overview` (live member count + recent chat), `GET /guild/{key}/members` (triggers `/guild list` + `/guild online` in-game, parses the output, syncs it to `guild_members`, and returns the merged online/offline member list — falls back to the DB cache if the bot isn't connected), `POST /restart/{key}`, `POST /stop/{key}`, `GET /api-usage`.

### `config.py`
- Loads all env vars and defines every scalar config constant the rest of the code imports.
- Defines `GuildConfig` dataclass — the single source of truth for per-guild settings:
  - `key` (`'bk'`/`'bu'`) — used as dict key everywhere
  - `display_name` / `short_name` — e.g. `'Bumble Kindergarten'` / `'BK'`
  - `mc_options` — passed directly to `mineflayer.createBot()`; `mc_username` property reads the username out of it
  - `guild_name` — matched against `/guild list` output and used for the Hypixel guild API sync
  - `staff_role_id`, `member_role_id` — Discord role IDs for permission checks
  - `ranks` — `{bot_rank_key: skyblock_level_requirement}` for auto-rankup
  - `discord_rank_map` — maps Hypixel guild rank names to bot rank keys, used by the background refresh task and auto-rank-on-join
  - `bridge_channel_id` / `officer_channel_id` — which Discord channels feed into this guild's MC chat (`None` = no Discord→MC listener for that guild)
- `GUILD_CONFIGS: dict[str, GuildConfig] = {'bk': BK_CONFIG, 'bu': BU_CONFIG}` — the master registry. **Adding a new guild = adding one entry here.**
- Also defines `BOT_IPC_PORT` and (read directly via `os.getenv`, not exported as a constant) `BOT_IPC_URL`/`BOT_IPC_SECRET`, consumed by `web/routes/bots.py`.

### `db/base.py` + `db/manager.py` + `db/queries/`
- `BaseQueries` (`db/base.py`) wraps a `psycopg2.pool.ThreadedConnectionPool` (min 1, max 10). `_cursor()` is a context manager that commits on success and rolls back on exception, so cog code never manages transactions manually.
- Each domain — Users, Dyes, Guild Members, Panel Users, API Usage Tracking, Message Counts — is its own mixin under `db/queries/`, inheriting `BaseQueries` for `self._cursor()`. See "Database Schema" below for the tables backing each. A handful of methods legitimately join across two tables (e.g. `UsersQueries.search_users_with_dye_counts` joins `users_dyes`, `DyesQueries.get_recent_drops` joins `users`) — they just live in the mixin for their primary table; no cross-mixin calls are needed since it's all plain SQL.
- `DatabaseManager` (`db/manager.py`) multiply-inherits all six query mixins and adds nothing else — it's a thin composition root. `db/__init__.py` builds the module-level `manager` singleton from `DATABASE_URL` — cogs do `from db import manager` and call `manager.<any method from any mixin>` exactly as before; the split is invisible to callers.
- `lib/get_uuid.py` and `lib/get_username.py` still talk to `users` directly (not through `DatabaseManager`) because they are synchronous low-level cache utilities called from non-cog contexts.

### `db/migrate.py`
- `run_migrations(dsn)` creates a `schema_migrations` tracking table if needed, then applies every `*.sql` file in `db/migrations/` whose numeric prefix isn't already recorded, committing after each file.
- Called at startup by **both** `main.py` and `web_main.py`, so either process can be started first/alone and the schema will be current.

### `cogs/bridge/bridge.py`
- `GuildBridge` is instantiated once per guild by its `setup()`. Each instance registers a Mineflayer `On(state.bot, "chat")` handler scoped to that guild's bot.
- **MC → Discord**: parses rank/player/message from guild chat, sends to the shared bridge or officer webhook, logs to `message_logs`, appends to `state.recent_chat` (guild chat only), increments the sender's message count via `manager.increment_message_count`, then relays to all *other* guild bots with a `[BK]`/`[BU]` prefix.
- **Discord → MC**: only active when `config.bridge_channel_id` is not `None` (currently only BK). Resolves the author's IGN from DB, formats the message (handling replies), sends to every guild bot, and increments the message count for the resolved guild.
- `.commands` in Minecraft or Discord chat are routed to `bridge_commands()` via `run_coroutine_threadsafe` (Mineflayer callbacks run in a thread, not the asyncio event loop).

### `cogs/bridge/connections.py`
- `GuildConnections` handles Mineflayer `spawn` and `end` events per guild.
- On `spawn`: marks `state.connected = True` and kicks off `_sync_guild_members_from_api()` on a background `threading.Thread` — this hits the Hypixel `/v2/guild` API directly (not the bridge's Mineflayer chat), resolves each member's IGN via `get_username()`, and calls `manager.sync_guild_members()` to reconcile the `guild_members` table.
- On `end`: if `state.manual_stop` was set (by the web panel's stop endpoint), it clears the flag and does **not** reconnect. Otherwise it schedules a reconnect via `run_coroutine_threadsafe(reconnect(), self.client.loop)`, which sleeps 5s, calls `start_mineflayer(account=config.key)` to get a fresh bot object, then `reload_bridge_cogs(client, config)` to rebind the `connections`/`bridge`/`message_handler` cogs to it — this now uses the bot's own running event loop rather than spinning up a separate one.
- `reload_bridge_cogs(client, config)` (module-level function, not a method) removes and re-adds those three cogs for one guild key. This re-runs their `__init__`, which creates fresh Mineflayer event bindings against the new bot instance; old bindings on the dead bot instance are abandoned. It's called from both the auto-reconnect path above and `bot_ipc.py`'s manual `/restart/{key}` endpoint — the two are the only places a bot instance gets replaced after startup.

### `cogs/bridge/message_handler.py`
- Listens to `messagestr` (raw text lines from Minecraft, not parsed chat).
- Accumulates `/guild list` output into `state.guild_list` and `/guild online` output into `state.guild_online`; both flags (`save_guild_list` / `save_guild_online`) are set externally, primarily by `bot_ipc.py`'s `/guild/{key}/members` endpoint (and `save_guild_list` also by the `/bk-guild list` / `/bu-guild list` slash commands).
- Detects system events (join, leave, kick, mute, unmute, promote, demote, invite result, join request) and sends embeds to bridge/officer/logs webhooks; join/leave/kick/promote/demote also update the `guild_members` table via regex-extracted IGN/rank.
- On a `joined the guild!` message, schedules `_auto_fetch_and_rank()`: waits 5s, resolves the new member's UUID, fetches their Skyblock stats, stores them, and immediately runs `guild_rank_change()` against the guild's starting rank so new members are correctly ranked without waiting for the background refresh cycle.
- For join requests, fetches the applicant's Skyblock level via `skyblock.Player` and includes it in the embed.

### `cogs/tasks/member_refresh.py`
- `MemberRefreshTask` is a `discord.ext.tasks` loop (`_MEMBER_INTERVAL = 5` seconds) that continuously refreshes exactly one guild member's stats per tick, picking `manager.get_oldest_stats_member()` (oldest `stats_fetched_at`, `NULL`s first) each time.
- Sized to the Hypixel budget of 300 req/5min: ~24 req/min reserved for this loop (2 calls per member every 5s), leaving ~36 req/min for user dot-commands. A full ~250-member cycle takes roughly 21 minutes.
- After updating stats, if the member's rank changed via `guild_rank_change()`, it writes the new Hypixel rank name back to `guild_members` immediately (via `config.discord_rank_map` reversed) — this avoids a race where the next cycle re-reads a stale/partial rank captured by `message_handler.py`'s regex and undoes the promotion.
- Waits 60s after `wait_until_ready()` before starting, so it doesn't compete with startup traffic.

### `utils/command_handler.py`
- `bridge_commands(client, message, username, guild_rank, chat_state, config)` dispatches `.help`, `.lvl`, `.hlvl`, `.nw`, `.slayer`/`.slayers`, `.slayerxp <type>`, `.cata`, `.rtca`, `.rtcaf`, `.pb`, `.mp`, `.bank`, `.chim <looting> <mf>`, `.petscore`.
- Each handler is a private `async` function that returns `(display_name, response_text, raw_username)`. The dispatcher sends the response to all guild bots and the appropriate webhook.
- There is no in-game `.ranks` command anymore — rank auto-updates happen continuously via `cogs/tasks/member_refresh.py` and immediately on join via `message_handler.py`'s `_auto_fetch_and_rank()`.

### `player/class_average.py`
- `ClassAverage` backs the `.rtca [username] [floor]` command (floor defaults to `m7`; the target is always class average 50). It reads `dungeons.player_classes.<class>.experience` — the only place in the codebase that touches class XP.
- `runs_to_target()` reproduces the reference calculator (`adjectiven0un/adjectils` `dungeon.html`): each run, the class with the most XP remaining is the one being played and earns full XP while the other four earn a quarter each. Below `_SIMULATION_LIMIT` projected runs it replays that loop exactly; above it (low floors, where the answer runs to millions of runs) it switches to an equivalent analytic solve so the event loop isn't stalled. Both agree on the total.
- `runs_to_target()` takes an optional `playable` subset (defaults to all 5, `DUNGEON_CLASSES`). `.rtcaf` passes a subset with 1-4 classes permanently excluded from ever being the "played" pick — all 5 classes still must reach `target_level`, but excluded classes can only ever earn the passive quarter share, never a full played run's XP. This makes excluding classes strictly *raise* the total run count (never lower it): the binary search in `__solve_total_runs` takes `max()` of the normal playable-class requirement and a `__skip_threshold` floor — the run count by which each excluded class's passive-only climb clears target on its own.
- `minimum_runs_needed()` reports, for a known total from `runs_to_target()`, the fewest dedicated plays each *playable* class needs — used only by `.rtcaf`. Once a playable class's minimum is met, further runs can go to any playable class interchangeably (passive share depends only on total runs elapsed, not on which other class got played), so `.rtcaf`'s reply shows per-class minimums only where nonzero and folds the rest into a single "then N runs, any class" tail. A class needing 0 means the total (usually inflated by the skip threshold) already covers it on passive share alone.
- XP boosts are read off the profile: Hecatomb from the NBT of every container in `_HECATOMB_CONTAINERS` plus every backpack (`_BACKPACKS_PATH`) — a player's dungeon gear is usually *not* what they have equipped when the profile is read, and has been observed in the wild sitting in the ender chest and inside a backpack, so anything narrower than a full sweep silently undercounts the boost by 4%, the Scarf accessory line from the talisman bag NBT, the per-class essence perks from `player_data.perks`, and Catacombs Graduate from `attributes.stacks.catacombs_graduate` (a shard count converted to a level via `ATTRIBUTE_LEVEL_THRESHOLDS`). The mayor multiplier comes from `lib/hypixel.py::fetch_mayor_multiplier()` (keyless `/v2/resources/skyblock/election`, cached 10 min). The reference's "global boost" dropdown has no API equivalent and is always 0.
- **Missing container means maxed, not zero.** If a whole container is absent — usually because the player has their inventory API off — that boost is assumed to be at its cap. This is deliberate: the run count comes out optimistic rather than silently doubled. A container that is present but lacks the key means the player genuinely has 0.

### `cogs/commands/guild_commands.py`
- Contains `BKGuild` and `BUGuild` as two `GroupCog` classes in one file. Shared helper `_guild_list_embed()` avoids duplication.
- Each class reads from `client.guilds_state['bk']` or `['bu']` rather than `client.bk_bot` directly.
- **To add a third guild:** add a new `GroupCog` subclass here and a line in `setup()`.

### `web/app.py`
- `create_app()` takes no arguments (there's no live `Client` in this process) and mounts `web/routes/bots.py`, `web/routes/users.py`, and `web/routes/dyes.py` as routers.
- Handles Discord OAuth2 callback: exchanges code for a Discord user object, auto-provisions the admin (`PANEL_ADMIN_DISCORD_ID`) as a `panel_users` row on first login, updates the stored Discord name/avatar on every login, issues a JWT, redirects to `/?token=...`.
- Serves `GET /api/me` (returns JWT claims as JSON, including `can_control_bots`/`can_fetch_api`/`can_manage_links`/`is_owner`).
- If `frontend/dist/` exists, mounts `/assets` as static files and serves `index.html` for all other routes (SPA fallback). The HTML is **read at startup and cached**; restart the web process after a frontend rebuild or it will serve a stale `index.html` referencing the old JS bundle. If `frontend/dist/` doesn't exist, every route returns a 503 telling you to build it.

### `web/auth.py`
- `discord_oauth_url()` builds the Discord OAuth2 authorization URL.
- `exchange_code(code)` exchanges the authorization code for the user's Discord profile dict via aiohttp.
- `create_token()` / `verify_token()` — HS256 JWT, **30-day** expiry. Payload keys: `sub` (discord_id str), `name`, `admin`, `bots` (can_control_bots), `fetch_api`, `manage_links`, `avatar`, `owner` (is `PANEL_ADMIN_DISCORD_ID`).
- FastAPI dependencies: `require_auth`, `require_admin`, `require_bot_control`, `require_api_fetch`, `require_manage_links`, `require_owner` — all read `Authorization: Bearer <token>` and raise `HTTPException` on failure. Each permission (except `admin`/`owner`) is satisfied by either its own flag or `admin`.

### `web/routes/dyes.py`
- All routes are `require_auth`-gated, read-only. `GET /api/dyes/me` — resolves the caller's uuid via `manager.get_user_by_discord`, returns `{"linked": false}` if unlinked. `GET /api/dyes/search?q=` — IGN search via `manager.search_users_with_dye_counts`. `GET /api/dyes/user/{uuid}` — another player's profile, 404 if unknown. `GET /api/dyes/recent` — the last 20 unlocks across all players via `manager.get_recent_drops`, newest first.
- `_build_profile()` merges `manager.get_all_dyes()` (the full catalog) with `manager.get_unlocked_dyes(uuid)` and computes each dye's `"1 in N"` odds the same way `roll_dye.py` does, so the number shown in the panel always matches the in-game announcement.

### `web/routes/bots.py`
- All routes are prefixed `/api/bots` and proxy to the bot process's IPC API (`BOT_IPC_URL`, default `http://localhost:8081`) using `aiohttp`, falling back to an "offline" shape (or a 503) if the bot process is unreachable.
- `GET /api/bots` (`require_bot_control`) — per-guild connection status.
- `GET /api/bots/{key}/overview` (`require_auth`) — live member count + recent chat, or an offline placeholder.
- `GET /api/bots/{key}/members` (`require_auth`) — proxies to `GET /guild/{key}/members` on the bot's IPC (which itself triggers `/guild list`/`/guild online` in-game).
- `POST /api/bots/{key}/restart` / `POST /api/bots/{key}/stop` (`require_bot_control`) — proxy to the bot's IPC restart/stop endpoints.
- `POST /api/bots/{key}/members/{ign}/link` / `DELETE .../link` (`require_manage_links`) — link/unlink a `guild_members` row's UUID to a Discord account directly from the panel (no in-game `/link` flow needed).
- `POST /api/bots/{key}/refresh-stats` / `GET /api/bots/{key}/stats-status` (`require_api_fetch`) — kicks off (and reports progress of) an eager, manual stats refresh for every member of a guild via a local `asyncio.create_task`, independent of the background `MemberRefreshTask` running in the bot process. Deliberately slower (1 req/s) since it's user-triggered and shares the same Hypixel budget.
- `GET /api/bots/api-usage` (`require_owner`) — combines local `api_calls` counts (`manager.get_api_call_counts()`) with live Hypixel key usage (`fetch_key_info()`).
- `GET /api/bots/{key}/leaderboard` (`require_auth`) — message-count leaderboard for `lifetime` / `month` / `week`, backed by `manager.get_message_leaderboard()`.

### `web/routes/users.py`
- CRUD for the `panel_users` table: list, create, update permissions, delete.
- All endpoints require admin. Self-demotion and self-deletion are blocked.

### `frontend/src/App.tsx`
- `AuthProvider` — reads `?token=` from URL on mount (OAuth redirect), stores in `localStorage`, fetches `/api/me`, exposes `{me, loading, logout}` context.
- `AppRouter` — unauthenticated users see `Login`; authenticated users see everything else nested inside a single `<Protected><AppShell/></Protected>` layout route: `Home` at `/`, `/guilds/:key`, `/guilds/:key/members`, `/guilds/:key/leaderboard`, `/dyes`, `/admin`, and `/users` (admin-only). There is no per-guild layout route anymore — each guild sub-page reads `:key` via `useParams` independently.
- `frontend/src/api.ts` centralizes all `fetch()` calls to the backend; `frontend/src/types.ts` holds shared TS types (`Me`, etc.).

### `frontend/src/components/AppShell.tsx`
- The persistent app chrome for every authenticated page: a fixed left sidebar (wordmark, Home link, both guilds' Overview/Members/Leaderboard sub-nav with a live connected/offline dot per guild polled from `api.bots()`, Dyes, and Admin/Users gated by `is_owner`/`is_admin`) plus a user chip with logout, and a `<main>` that renders the active page via `<Outlet/>`. Individual pages no longer render their own header — this replaced four separate hand-rolled headers (`Home.tsx`, the old `GuildLayout.tsx`, `Admin.tsx`, `Users.tsx`) that had drifted out of sync with each other.

### `frontend/src/components/IdentityCell.tsx` + `Modal.tsx`
- `PlayerIdentityCell` (Minecraft avatar + IGN, optional badge) and `DiscordIdentityCell` (Discord avatar + name, optional id/actions, em-dash placeholder when unlinked) — the two identity-cell shapes repeated in every member/leaderboard table. Used by `GuildMembers.tsx` and `GuildLeaderboard.tsx`.
- `Modal` — the overlay+card+title+actions shell shared by every "form in a modal" flow (closes on backdrop click). Used by `GuildMembers.tsx`'s link/unlink modal and `Users.tsx`'s create/edit modal.

### `frontend/src/hooks/usePolling.ts` + `frontend/src/lib/`
- `usePolling(callback, intervalMs, deps)` — runs `callback` immediately then every `intervalMs` until unmount or a `deps` change restarts it. Used by `AppShell.tsx` (bot status, 15s), `GuildOverview.tsx` (overview, 15s), and `Admin.tsx`'s `ApiUsagePanel` (API usage, 30s). `GuildMembers.tsx`'s stats-refresh progress poll is a different shape (polls until a "done" flag rather than forever) and stays a local `setInterval` in that file.
- `lib/time.ts::formatRelativeTime(diffMs, opts)` — the "Xm/Xh/Xd ago" formatter shared by `GuildMembers.tsx` (`formatLastLogin`/`formatFetchedAt`) and `Dyes.tsx` (`timeAgo`); each caller passes options (`justNowUnderMins`, `maxTier`) to reproduce its own exact tier cutoffs rather than the three near-duplicate implementations there used to be.
- `lib/validators.ts::isValidDiscordId()` — the `/^\d{17,20}$/` check duplicated between `GuildMembers.tsx`'s link modal and `Users.tsx`'s create-user form.

### `frontend/src/pages/*.tsx`
- `Login.tsx` — Discord OAuth2 login screen.
- `Home.tsx` — landing content after login (guild picker), chrome-free — just the page body, rendered inside `AppShell`.
- `GuildOverview.tsx` — connection status, member count, recent chat for one guild.
- `GuildMembers.tsx` — member list/table (rank, Skyblock level, last login, linked Discord account), backed by `GET /api/bots/{key}/members`.
- `GuildLeaderboard.tsx` — message-count leaderboard (lifetime/month/week), backed by `GET /api/bots/{key}/leaderboard`.
- `Admin.tsx` — bot control (start/stop/restart), manual stats refresh, API usage.
- `Users.tsx` — table of all panel users with add/edit/delete (admin only).
- `Dyes.tsx` — a player's own dye profile by default (`GET /api/dyes/me`), IGN search to view another player's (`GET /api/dyes/search` → `GET /api/dyes/user/{uuid}`), a "Recently Dropped" feed (`GET /api/dyes/recent`), and the full catalog with locked dyes shown desaturated (no lock icon) alongside their odds. Dye artwork is hotlinked directly from the Hypixel Skyblock wiki (`https://hypixelskyblock.minecraft.wiki/images/{Dye_Name}.png`, spaces replaced with underscores) rather than bundled — verified working for all 34 dyes but is an external dependency worth knowing about if it ever needs to move to a bundled asset.

There is no log-streaming page — `Logs.tsx`, its `/ws/logs` backend endpoint, and `web/logs.py` (`LogBroadcaster`/`WebLogHandler`) were removed as unused.

---

## Dependencies

### Python (`requirements.txt`)
| Package | Why |
|---------|-----|
| `discord.py >= 2.6.4` | Discord bot framework — slash commands, webhooks, events |
| `javascript >= 1!1.2.6` | Bridges Python ↔ Node.js; lets Python call Mineflayer and skyhelper |
| `python-dotenv` | Loads `.env` file into `os.environ` |
| `aiohttp` | Async HTTP for `lib/fetch.py`, `lib/hypixel.py`, Discord OAuth2 token exchange, and the web→bot IPC calls |
| `requests` | Sync HTTP for `lib/fetch.py` and the Mineflayer-thread Hypixel guild sync in `connections.py` |
| `emoji` | Converts Discord emoji to text (`:bee:`) before sending to Minecraft |
| `NBT` | Decodes base64-encoded NBT data from talisman bags (magical power calc) |
| `fastapi >= 0.115.0` | Both the web panel API and the bot process's internal IPC API |
| `uvicorn >= 0.32.0` | ASGI server — runs the panel and IPC FastAPI apps |
| `PyJWT >= 2.10.0` | JWT creation and verification for stateless panel sessions |
| `pydantic >= 2.0.0` | Request body validation for FastAPI routes |
| `psycopg2-binary >= 2.9.0` | PostgreSQL driver used by `db/manager.py` and `db/migrate.py` |

### Node.js (`package.json`)
| Package | Why |
|---------|-----|
| `mineflayer` | Minecraft bot client — connects to Hypixel, sends/receives chat |
| `skyhelper-networth` | Calculates player net worth from profile data; called via the `javascript` bridge |

### Frontend (`frontend/package.json`)
| Package | Why |
|---------|-----|
| `react` / `react-dom` | UI framework |
| `react-router-dom` | Client-side routing (Home, guild pages, Admin, Users, Logs) |
| `vite` | Build tool; also runs a dev server that proxies `/api` and `/ws` to the Python backend |
| `typescript` | Type safety across all frontend code |

---

## Architecture: How the Pieces Connect

```
Discord Server
    │
    │  webhooks (SyncWebhook)         slash commands (app_commands)
    ▼                                         ▼
Client (bot/main.py)  ◄──────────────  cogs/commands/*.py
    │                                         │
    │  guilds_state['bk'].bot                 │  db/manager.py (psycopg2 pool)
    │  guilds_state['bu'].bot                 │
    ▼                                         ▼
Mineflayer bots (JS/Node.js)          PostgreSQL (DATABASE_URL)
    │                                         ▲
    │  On("chat") / On("messagestr")          │  same DB, no shared process memory
    ▼                                         │
cogs/bridge/bridge.py        →  utils/command_handler.py  →  player/*.py  →  Hypixel API
cogs/bridge/message_handler.py
cogs/bridge/connections.py
cogs/tasks/member_refresh.py

bot_ipc.py (127.0.0.1:BOT_IPC_PORT, inside the bot process)
    ▲
    │  HTTP + X-IPC-Secret
    │
web/routes/bots.py  (inside the web/panel process, bot/web_main.py)
    │
    ▼
frontend/dist (React SPA served by web/app.py)
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

**Request path for the web panel's member list (`GET /api/bots/{key}/members`):**
1. Panel process (`web/routes/bots.py`) makes an authenticated HTTP call to the bot process's IPC API
2. `bot_ipc.py`'s `get_guild_members()` sends `/guild list` and `/guild online` in-game, waits 1.5s each, and parses the accumulated `messagestr` lines via `lib/guild_list.py`
3. Parsed results are written to `guild_members` via `manager.sync_guild_members()`
4. The merged member list (DB stats + live online status) is returned to the panel

---

## Data Flow

### Minecraft → Discord
```
Mineflayer "chat" event
  → GuildBridge parses rank/player/message via regex
  → Sends to bridge or officer SyncWebhook
  → Increments message_counts, appends to state.recent_chat
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
  → Updates guild_members (upsert/remove) for join/leave/kick/promote/demote
  → On join: schedules _auto_fetch_and_rank() (fetch stats + rank immediately)
```

### Background member refresh (rank automation)
```
cogs/tasks/member_refresh.py, every 5s
  → manager.get_oldest_stats_member() picks the member due for a refresh
  → Fetches Skyblock level + last_login from Hypixel
  → guild_rank_change() promotes/demotes if the level crossed a threshold
  → Writes the new rank back to guild_members immediately to avoid races
```

### Auto-reconnect
```
Mineflayer "end" event
  → GuildConnections sends disconnect embed (unless state.manual_stop)
  → run_coroutine_threadsafe(reconnect(), client.loop): sleep 5s, then
    client.start_mineflayer(account=config.key)
  → cogs.bridge.connections.reload_bridge_cogs(client, config) reloads
    connections/bridge/message_handler cogs against the new bot instance
```

---

## Database Schema

PostgreSQL, accessed exclusively through `psycopg2` (`db/manager.py`). Schema is managed by numbered migrations in `db/migrations/`, applied by `db/migrate.py` and tracked in a `schema_migrations` table. Both `main.py` and `web_main.py` run migrations on startup.

Core tables (see the migration files for exact DDL/history — `ign` columns use `citext` for case-insensitive matching, added in migration 004):

```sql
users (
    uuid            TEXT PRIMARY KEY,
    ign             TEXT,
    discord_id      BIGINT UNIQUE,     -- NULL until linked
    discord_name    TEXT,              -- NULL until linked
    discord_avatar  TEXT               -- NULL until linked; avatar URL, refreshed on every login
);

dyes (
    dye_id   TEXT PRIMARY KEY,
    dye_name TEXT,
    weight   REAL,                     -- higher weight = more common drop
    hex      TEXT                      -- color hex for embed, e.g. "FF3C3C"
);

users_dyes (
    uuid         TEXT REFERENCES users(uuid),
    dye_id       TEXT REFERENCES dyes(dye_id),
    received     BOOLEAN DEFAULT FALSE,
    unlocked_at  TIMESTAMPTZ,              -- set on every mark_dye_received(); powers the "recently dropped" feed
    UNIQUE (uuid, dye_id)
);

panel_users (
    discord_id        BIGINT PRIMARY KEY,
    discord_name      TEXT,
    is_admin          BOOLEAN DEFAULT FALSE,
    can_control_bots  BOOLEAN DEFAULT FALSE,
    can_fetch_api     BOOLEAN DEFAULT FALSE,
    can_manage_links  BOOLEAN DEFAULT FALSE
);

guild_members (
    guild_key         TEXT,            -- 'bk' / 'bu'
    ign               CITEXT,
    uuid              TEXT,
    rank              TEXT,
    skyblock_level    REAL,
    last_login        BIGINT,
    stats_fetched_at  BIGINT,          -- unix seconds; NULL = never fetched, refreshed first
    PRIMARY KEY (guild_key, ign)
);

message_counts (
    guild_key    TEXT,
    uuid         TEXT,
    ign          TEXT,
    period_type  TEXT,                 -- 'lifetime' / 'month' / 'week'
    period_key   TEXT,                 -- '' for lifetime, 'YYYY-MM' for month, ISO 'GGGG-Www' for week
    count        INTEGER DEFAULT 0,
    UNIQUE (guild_key, uuid, period_type, period_key)
);

api_calls (
    called_at  TIMESTAMPTZ,
    endpoint   TEXT,
    success    BOOLEAN
);
```

Notes:
- `guild_members` is the roster source of truth for the web panel and background refresh; it's kept in sync three ways: the Hypixel `/v2/guild` API on bot spawn (`connections.py`), `/guild list` parsing on demand (`bot_ipc.py`'s members endpoint), and regex-matched system messages (`message_handler.py`).
- `message_counts` is only incremented for IGNs that resolve to a `guild_members` row with a non-empty UUID — messages from players not yet synced to the roster aren't counted.
- `api_calls` is written by `lib/hypixel.py` on every Hypixel API request and read by `manager.get_api_call_counts()` for the panel's API usage view.
- UUID resolution (`get_uuid` / `get_username`) always writes to `users` as a side effect, so `users` doubles as a UUID↔IGN cache even for players who never link their Discord.

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
- `lib/hypixel.py::fetch_member_stats()` — async, aiohttp-based, used by both the background refresh task and the panel's manual refresh endpoint; records every call to `api_calls`.

### DatabaseManager usage
All cog-level and web-route DB access goes through `from db import manager` and calls its typed methods. Direct `sqlite3`/`psycopg2` access is only acceptable inside `lib/get_uuid.py`, `lib/get_username.py`, and `db/migrate.py` (low-level utilities predating/outside the manager).

### Webhook vs interaction response
- Bridge messages use `SyncWebhook.send()` (synchronous, called from threads or sync contexts)
- Slash command responses use `await interaction.response.send_message()` or `await interaction.edit_original_response()` after `defer()`

### Deferred interactions
Any slash command that does I/O (DB, Hypixel API, `asyncio.sleep`) must call `await interaction.response.defer()` first, then `await interaction.edit_original_response(embed=embed)` when done. Commands that are instant (mute, unmute, kick) can use `send_message()` directly.

### Web panel permissions
Panel permissions are per-flag (`can_control_bots`, `can_fetch_api`, `can_manage_links`) plus `is_admin` (grants everything) and `is_owner` (matches `PANEL_ADMIN_DISCORD_ID`, gates only `/api/bots/api-usage`). New panel endpoints should pick the narrowest matching `require_*` dependency from `web/auth.py` rather than defaulting to `require_admin`.

---

## Things to Watch Out For

### The `javascript` bridge is threaded
All Mineflayer event handlers (`@On`, `@Once`) run in their own thread. Accessing `client` attributes from inside them is safe for reads, but any mutation of shared state (like `state.guild_list`) must be treated carefully. Currently the only writes are appends to lists and simple flag assignments, which is safe enough in CPython due to the GIL.

### Reconnect reloads bridge extensions
`cogs/bridge/connections.py::reload_bridge_cogs(client, config)` removes and re-adds the `connections`, `bridge`, and `message_handler` cogs for that guild key, always immediately after `client.start_mineflayer(account=config.key)` creates a fresh bot object. This re-runs their `__init__`, which creates fresh Mineflayer event bindings against the new bot instance. Old bindings on the dead bot instance are abandoned. If you add new bridge modules, add their reload to `reload_bridge_cogs()`'s suffix list.

### The bot and web processes are independent
`web/routes/bots.py` never touches a live `Client` object — it only reaches the bot process via HTTP IPC (`BOT_IPC_URL`/`BOT_IPC_SECRET`) or reads shared PostgreSQL state. If the bot process is down, IPC calls fail and routes fall back to DB-cached/offline data (or a 503) rather than crashing. Don't reintroduce a shared in-process `Client` reference between the two — they are meant to be deployable and restartable independently.

### Guild list race condition
Both `/bk-guild list`/`/bu-guild list` and `bot_ipc.py`'s `/guild/{key}/members` endpoint send `/guild list` (and `/guild online`) to Minecraft and then sleep before reading the accumulated buffer (`state.guild_list` / `state.guild_online`). If two callers trigger this concurrently, the buffers can interleave. The sleep is a best-effort wait, not a proper lock — don't add more concurrent consumers of these buffers without addressing this.

### `skyblock.Player` is synchronous and slow
`Player.__init__` makes multiple blocking HTTP requests (Mojang UUID lookup, Hypixel profiles). It should never be constructed inside a Mineflayer callback directly — always schedule it via `run_coroutine_threadsafe` and use an async wrapper. Bridge commands already do this correctly.

### Frontend rebuild requires web process restart
`web/app.py` reads `frontend/dist/index.html` once at startup and caches it in memory. After running `npm run build`, the new JS bundle gets a new filename hash. If the web process is not restarted it will keep serving the old `index.html`, which references the missing old bundle — the browser loads a blank page. Always restart `web_main.py` (not `main.py`) after a frontend rebuild.

### panel_users is a separate table from users
`panel_users` holds web panel access control and is completely separate from `users` (which stores Discord↔Minecraft links). A user can exist in `users` without being in `panel_users` and vice versa. The first login by `PANEL_ADMIN_DISCORD_ID` auto-creates their `panel_users` row as admin if it doesn't exist yet.

### JWT permissions are baked in at login time
The JWT encodes `admin`/`bots`/`fetch_api`/`manage_links`/`owner` at the moment of login and is valid for 30 days. If an admin changes a user's permissions in the Users panel, the change takes effect only after that user's token expires and they log in again. There is no token revocation mechanism.

### Hypixel API budget is shared and tight
The key is limited to 300 requests/5min. `cogs/tasks/member_refresh.py` reserves ~24 req/min for its continuous background cycle; the panel's manual "refresh stats" button (`web/routes/bots.py::_do_refresh_stats`) deliberately paces itself at 1 request/second to avoid starving both the background loop and live dot-commands. Any new bulk Hypixel-calling feature must budget against this same 300/5min ceiling — check `GET /api/bots/api-usage` before adding one.

### `.rtca` shard rarity is inferred
The boost paths in `player/class_average.py` are confirmed against a live profile: class perks are `player_data.perks.<perk>` (a plain level 0-5), and Catacombs Graduate is `attributes.stacks.catacombs_graduate`. That last one is a **shard count, not a level** — the level comes from `ATTRIBUTE_LEVEL_THRESHOLDS`, which differs per shard rarity, and `CATA_GRADUATE_SHARD_RARITY` is set to `epic` on the evidence of one maxed account sitting at exactly 32 shards. If the Scarf shard is actually another rarity, that constant is the only thing to change.

Also note the top-level `shards` object is the shard *inventory* (`owned`, `fused`, sort settings) and carries no attribute progress — don't reach for it.

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
6. Everything else (bridge relay, background rank refresh, reconnect, web panel guild pages) picks up the new guild automatically from `GUILD_CONFIGS`

---

## Environment Variables

See `example.env` for the full list. Critical ones:

| Variable | Used by |
|----------|---------|
| `DISCORD_BOT_TOKEN` | `config.py` → `main.py` login |
| `HYPIXEL_API_KEY` | All Hypixel API requests in `lib/` and `player/` |
| `DATABASE_URL` | PostgreSQL connection string — `db/__init__.py`, `db/migrate.py` |
| `KINDERGARTEN_USERNAME` / `UNIVERSITY_USERNAME` | Mineflayer login; also used to filter the bot's own messages |
| `KINDERGARTEN_LOGS_CHANNEL` / `UNIVERSITY_LOGS_CHANNEL` | Per-guild logs `SyncWebhook` URLs |
| `BRIDGE_CHANNEL` / `OFFICER_CHANNEL` | Shared bridge/officer `SyncWebhook` URLs |
| `BRIDGE_CHANNEL_ID` / `OFFICER_CHANNEL_ID` | `GuildBridge.on_message` channel filter (BK) |
| `BK_STAFF_ROLE_ID` / `BU_STAFF_ROLE_ID` | Slash command permission checks |
| `EXEC_ROLE_ID` | `/admin` and `/bk-exec`/`/bu-exec` permission checks |
| `BOT_IPC_PORT` | Port the bot process's internal IPC API listens on (default 8081), bound to `127.0.0.1` only |
| `BOT_IPC_URL` | Base URL the web process uses to reach the bot's IPC API (default `http://localhost:8081`) |
| `BOT_IPC_SECRET` | Shared secret sent as `X-IPC-Secret`; required by `bot_ipc.py` if set |
| `PANEL_PORT` | Port uvicorn listens on for the web panel (default 8080) |
| `PANEL_DISCORD_CLIENT_ID` | Discord OAuth2 app client ID (`web/auth.py`) |
| `PANEL_DISCORD_CLIENT_SECRET` | Discord OAuth2 app client secret (`web/auth.py`) |
| `PANEL_REDIRECT_URI` | OAuth2 redirect URI, e.g. `https://bumble.seazyns.dev/auth/callback` |
| `PANEL_JWT_SECRET` | Random secret for signing JWTs — keep private |
| `PANEL_ADMIN_DISCORD_ID` | Discord ID of the panel owner; auto-provisioned as admin on first login, gates `require_owner` |
