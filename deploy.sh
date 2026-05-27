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

echo "Restarting bot..."
pm2 restart bumble-bot

echo "Restarting web..."
pm2 restart bumble-web

echo "Done."
