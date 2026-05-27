#!/bin/bash
set -e

cd ~/bumble-unified

echo "Pulling latest changes..."
git stash
git pull

echo "Installing Python dependencies..."
source venv/bin/activate
pip install -r bot/requirements.txt

echo "Installing Node dependencies..."
cd bot
npm install
cd ..

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Restarting services..."
pm2 restart bumble-bot
pm2 restart bumble-web

echo "Done."
