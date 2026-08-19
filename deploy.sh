#!/bin/bash
set -e

# === Non-interactive SSH needs explicit PATH ===
export PATH="/home/deploy/.nvm/versions/node/v24.18.0/bin:$PATH"

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX → Starting deploy for dinepixel-api"

cd /home/deploy/dinepixel-api

echo "$LOG_PREFIX → Pulling latest code..."
git pull origin main

echo "$LOG_PREFIX → Activating virtualenv..."
source .venv/bin/activate

echo "$LOG_PREFIX Python: $(python --version), pip: $(pip --version | awk '{print $2}'), pm2: $(pm2 -v)"

echo "$LOG_PREFIX → Installing/updating dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "$LOG_PREFIX → Restarting PM2 process..."
pm2 restart dinepixel-api --update-env
pm2 save

echo "$LOG_PREFIX ✓ Deploy complete"
