#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Starting backend, frontend, and database in detached mode..."
docker compose -f docker-compose.yml up --build -d

echo "Application stack is running in the background."
echo "Use 'docker compose -f docker-compose.yml down' to stop it."
