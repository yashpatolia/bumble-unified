#!/bin/bash
set -e

cd ~/bumble-unified

echo "Pulling latest changes..."
git stash
git pull

echo "Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Restarting services..."
pm2 restart bumble-bot
pm2 restart bumble-web

echo "Done."
