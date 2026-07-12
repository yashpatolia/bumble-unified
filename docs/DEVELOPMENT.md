# Development Guide

## Testing

### Prerequisites

Install the two test-only packages (on the machine where you run tests):

```bash
pip install pytest pytest-asyncio
```

The full `requirements.txt` stack does **not** need to be installed locally — `conftest.py` stubs every heavy dependency (psycopg2, discord, aiohttp, etc.) so the pure-function tests run anywhere.

---

### Running the test suite

```bash
cd bot
pytest
```

Run with verbose output to see each test name:

```bash
pytest -v
```

Run a single file:

```bash
pytest tests/test_parsers.py -v
```

---

### What is tested

| File | Covers |
|---|---|
| `tests/test_parsers.py` | `parse_guild_list` and `parse_online_igns` — guild list / online text parsing |
| `tests/test_rankup.py` | `guild_rank_change` — promotion, demotion, no-change, empty-rank fallback, known_level skips API |
| `tests/test_utils.py` | `condense` — number formatting; `deep_get` — nested dict access |

---

### Adding new tests

1. Create `bot/tests/test_<module>.py`.
2. Import what you need — the conftest stubs are already active for the whole session.
3. For async functions, just write `async def test_...` — `asyncio_mode = auto` in `pytest.ini` handles it.
4. For anything that would call a real external service (DB, Hypixel, Discord), use `unittest.mock.patch` or `MagicMock`.

---

## Copying the production database locally

This pulls a live snapshot of the VPS database to your local machine for testing or debugging. It streams `pg_dump` over SSH directly into local `pg_restore` — no temp files, no tunnel needed.

### Prerequisites (local machine)

```bash
# macOS
brew install libpq
brew link --force libpq
```

`pg_restore`, `createdb`, and `dropdb` must all be in your `PATH`. The script checks and will tell you if anything is missing.

---

### Steps

**1. Run the script:**

```bash
bash scripts/copy-prod-db.sh user@your-vps-ip
```

Replace `user@your-vps-ip` with your actual SSH connection string, e.g. `seazyns@1.2.3.4`.

The script reads `DATABASE_URL` from `~/bumble-unified/.env` on the VPS. If your project lives at a different path, edit the `REMOTE_ENV` line near the top of the script.

By default it creates a local database called `bumble_test`. Pass a second argument to use a different name:

```bash
bash scripts/copy-prod-db.sh seazyns@1.2.3.4 my_local_db
```

**2. Run the tests against it:**

```bash
cd bot
DATABASE_URL=postgresql://localhost/bumble_test pytest
```

---

### Notes

- The script drops and recreates the local DB each time, so it's always a clean copy.
- Your SSH key must be authorised on the VPS (standard `~/.ssh/id_rsa` setup).
- The VPS must have `pg_dump` installed — it will if PostgreSQL is installed there.
