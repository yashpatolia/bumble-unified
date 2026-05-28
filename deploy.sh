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

if echo "$CHANGED" | grep -q '^bot/'; then
    echo "Installing Python dependencies..."
    source venv/bin/activate
    pip install -r bot/requirements.txt

    echo "Installing Node dependencies..."
    cd bot && npm install && cd ..
fi

if echo "$CHANGED" | grep -q '^frontend/'; then
    echo "Building frontend..."
    cd frontend && npm install && npm run build && cd ..
fi

echo "Running database migrations..."
source venv/bin/activate
cd bot && export $(grep -v '^#' .env | xargs) && python -m db.migrate && cd ..

echo "Restarting bot..."
pm2 stop bumble-bot || true
fuser -k 8081/tcp 2>/dev/null || true
sleep 1
pm2 start bumble-bot

echo "Restarting web..."
pm2 restart bumble-web

echo "Done."
