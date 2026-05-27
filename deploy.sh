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

RESTART_BOT=0
RESTART_WEB=0
BUILD_FRONTEND=0

# bot/ changes affect both processes (shared config, db, web routes)
if echo "$CHANGED" | grep -q '^bot/'; then
    RESTART_BOT=1
    RESTART_WEB=1
fi

# frontend changes only affect the web process
if echo "$CHANGED" | grep -q '^frontend/'; then
    BUILD_FRONTEND=1
    RESTART_WEB=1
fi

if [ "$RESTART_BOT" = "1" ]; then
    echo "Installing Python dependencies..."
    source venv/bin/activate
    pip install -r bot/requirements.txt

    echo "Installing Node dependencies..."
    cd bot && npm install && cd ..
fi

if [ "$BUILD_FRONTEND" = "1" ]; then
    echo "Building frontend..."
    cd frontend && npm install && npm run build && cd ..
fi

if [ "$RESTART_BOT" = "1" ]; then
    echo "Restarting bot..."
    pm2 restart bumble-bot
fi

if [ "$RESTART_WEB" = "1" ]; then
    echo "Restarting web..."
    pm2 restart bumble-web
fi

echo "Done."
