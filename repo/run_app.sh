#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Starting MeridianOps stack (backend + frontend + database)..."
docker compose -f docker-compose.yml up --build -d

echo ""
echo "Services:"
echo "  Backend API:  http://localhost:8000/api/v1/health"
echo "  Frontend app: http://localhost:5173"
echo "  PostgreSQL:   localhost:5432"
echo ""
echo "Stack is running in detached mode."
