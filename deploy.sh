#!/bin/bash
set -e

cd ~/bumble-unified

echo "Pulling latest changes..."
git stash
OLD_HEAD=$(git rev-parse HEAD)
git pull
CHANGED=$(git diff --name-only "$OLD_HEAD" HEAD)

if [ -z "$CHANGED" ]; then
    echo "Nothing changed, skipping restarts."
    exit 0
fi

# Ensure venv exists and is active before anything that needs Python
if [ ! -d "venv" ]; then
    echo "Creating virtualenv..."
    python3 -m venv venv
fi
source venv/bin/activate

if echo "$CHANGED" | grep -q '^bot/'; then
    echo "Installing Python dependencies..."
    pip install -r bot/requirements.txt

    # npm ci installs exactly what bot/package-lock.json pins (and wipes anything stale).
    # The bot loads these through bot/js_deps.js, so this is what actually runs.
    echo "Installing Node dependencies..."
    (cd bot && npm ci)

    # JSPyBridge keeps a private node_modules inside the venv for bare require() calls.
    # Nothing uses it any more (see bot/js_deps.js), so drop the stale copy if it exists.
    rm -rf venv/lib/python3*/site-packages/javascript/js/node_modules
fi

if echo "$CHANGED" | grep -q '^frontend/'; then
    echo "Building frontend..."
    (cd frontend && npm ci && npm run build)
fi

echo "Running database migrations..."
cd bot && set -a && source .env && set +a && python -m db.migrate && cd ..

echo "Restarting bot..."
pm2 stop bumble-bot || true
fuser -k 8081/tcp 2>/dev/null || true
sleep 1
pm2 start bumble-bot

echo "Restarting web..."
pm2 restart bumble-web

echo "Done."
