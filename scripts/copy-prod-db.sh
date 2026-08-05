#!/usr/bin/env bash
# Pull the production PostgreSQL database from your VPS to local.
#
# Streams pg_dump output directly over SSH — no temp files, no tunnel.
#
# Usage:
#   bash scripts/copy-prod-db.sh <user@host> [local_db_name]
#
# Example:
#   bash scripts/copy-prod-db.sh seazyns@1.2.3.4
#   bash scripts/copy-prod-db.sh seazyns@1.2.3.4 bumble_test
#
# Requirements:
#   Local : pg_restore, createdb, dropdb
#           macOS: brew install libpq && brew link --force libpq
#   VPS   : pg_dump (already there if PostgreSQL is installed)

set -euo pipefail

VPS="${1:?Usage: $0 user@vps-host [local_db_name]}"
LOCAL_DB="${2:-bumble_test}"

# Path to .env on the VPS — adjust if your project lives elsewhere
REMOTE_ENV="~/bumble-unified/.env"

echo "────────────────────────────────────────"
echo "  VPS      : $VPS"
echo "  Local DB : $LOCAL_DB"
echo "────────────────────────────────────────"
echo ""

# ── Verify local tools are available ──────────────────────────────────────
for cmd in pg_restore createdb dropdb; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not found locally."
    echo "  macOS: brew install libpq && brew link --force libpq"
    exit 1
  fi
done

# ── Recreate local database ────────────────────────────────────────────────
echo "▶ Recreating local database '$LOCAL_DB' ..."
dropdb --if-exists "$LOCAL_DB"
createdb "$LOCAL_DB"

# ── Stream dump from VPS → restore locally ─────────────────────────────────
# The heredoc runs entirely on the VPS:
#   - reads DATABASE_URL out of the remote .env
#   - runs pg_dump (stdout streams back over SSH)
# pg_restore on the local side reads that stream and loads it into LOCAL_DB.
echo "▶ Streaming dump from VPS (this may take a moment) ..."
echo ""

ssh "$VPS" REMOTE_ENV="$REMOTE_ENV" 'bash -s' <<'ENDSSH' \
  | pg_restore --no-owner --no-acl --dbname="$LOCAL_DB"

set -e
DB_URL=$(grep -m1 '^DATABASE_URL=' "$REMOTE_ENV" | cut -d= -f2-)
if [[ -z "$DB_URL" ]]; then
  echo "ERROR: DATABASE_URL not found in $REMOTE_ENV" >&2
  exit 1
fi
pg_dump "$DB_URL" --no-owner --no-acl --format=custom
ENDSSH

echo ""
echo "✓ Done. '$LOCAL_DB' is ready."
echo ""
echo "Point the bot at it:"
echo "  DATABASE_URL=postgresql://localhost/$LOCAL_DB python bot/main.py"
