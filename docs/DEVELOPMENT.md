# Development Guide

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

**2. Point the bot at it:**

```bash
DATABASE_URL=postgresql://localhost/bumble_test python bot/main.py
```

---

### Notes

- The script drops and recreates the local DB each time, so it's always a clean copy.
- Your SSH key must be authorised on the VPS (standard `~/.ssh/id_rsa` setup).
- The VPS must have `pg_dump` installed — it will if PostgreSQL is installed there.
