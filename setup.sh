#!/usr/bin/env bash
set -e

echo ""
echo "Personal Assistant — Setup Script"
echo "=================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "IMPORTANT: Edit .env and fill in your API keys before continuing."
  echo ""
  echo "  Minimum required to start:"
  echo "    ABACUS_API_KEY   — your Abacus AI API key"
  echo "    POSTGRES_PASSWORD — change from default"
  echo "    AGENT_SECRET_KEY  — change from default"
  echo "    N8N_ENCRYPTION_KEY — change from default (must be 32+ chars)"
  echo ""
  read -p "Press Enter after you have edited .env to continue, or Ctrl+C to stop..."
else
  echo ".env already exists, skipping copy."
fi

echo ""
echo "Starting stack..."
docker compose pull --quiet
docker compose up -d --build

echo ""
echo "Waiting for services to be healthy..."
sleep 10

RETRIES=20
for i in $(seq 1 $RETRIES); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' assistant-agent-core 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "Agent Core is healthy."
    break
  fi
  echo "  Waiting for agent-core... ($i/$RETRIES)"
  sleep 5
done

echo ""
echo "Importing n8n workflows..."
if command -v python3 &>/dev/null; then
  N8N_BASIC_AUTH_USER=$(grep N8N_BASIC_AUTH_USER .env | cut -d= -f2) \
  N8N_BASIC_AUTH_PASSWORD=$(grep N8N_BASIC_AUTH_PASSWORD .env | cut -d= -f2) \
  python3 import-workflows.py || echo "Workflow import failed — you can import them manually via the n8n UI."
else
  echo "python3 not found, skipping workflow import. Import manually via n8n UI."
fi

echo ""
echo "=============================="
echo "Stack is running!"
echo ""
echo "  Chat UI (Open WebUI):  http://localhost:3000"
echo "  n8n Automation:        http://localhost:5678"
echo "  Agent Core API:        http://localhost:8000"
echo "  Agent Core Docs:       http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "  1. Open n8n at http://localhost:5678 and connect your Gmail OAuth2 credentials"
echo "  2. Open n8n and add your Telegram bot token credential"
echo "  3. In n8n credentials, add 'Agent Core API Key' HTTP Header Auth:"
echo "     Header: Authorization   Value: Bearer <your AGENT_SECRET_KEY from .env>"
echo "  4. Activate the Telegram Bot and Daily Briefing workflows in n8n"
echo "  5. Open http://localhost:3000 and start chatting!"
echo ""
