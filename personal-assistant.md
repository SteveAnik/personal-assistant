# Personal AI Assistant — Docker Compose + n8n

## What We Are Building

A self-hosted, OpenHands-inspired personal AI agent that:
- Lives entirely on your home server as a Docker Compose stack
- Uses OpenAI / Anthropic APIs as the AI brain
- Uses n8n as the automation/workflow backbone
- Has a chat web UI, a Telegram bot interface, and scheduled jobs
- Has persistent memory across sessions
- Integrates with your existing stack: Home Assistant, Nextcloud, Plex/Jellyfin, Proxmox/Portainer, Gmail

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose Stack                │
│                                                     │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │  Open WebUI  │    │        n8n               │   │
│  │ (Chat UI)    │    │  (Workflow Automation)   │   │
│  └──────┬───────┘    └──────────┬───────────────┘   │
│         │                       │                   │
│         └──────────┬────────────┘                   │
│                    ▼                                 │
│         ┌─────────────────────┐                     │
│         │   Agent Core API    │  ← custom FastAPI   │
│         │  (tool calling +    │    service          │
│         │   orchestration)    │                     │
│         └──────────┬──────────┘                     │
│                    │                                 │
│         ┌──────────▼──────────┐                     │
│         │  Postgres + pgvector│  ← memory + vectors │
│         └─────────────────────┘                     │
│                                                     │
│  ┌──────────────┐  ┌────────────────┐               │
│  │  Playwright  │  │  Telegram Bot  │               │
│  │ (headless    │  │  (n8n webhook) │               │
│  │  browser)    │  └────────────────┘               │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
         │ integrations (local network)
         ▼
  Home Assistant / Nextcloud / Plex / Proxmox / Gmail
```

---

## Components & Roles

| Component | Image | Role |
|---|---|---|
| **Open WebUI** | `ghcr.io/open-webui/open-webui` | Primary chat interface in browser |
| **Agent Core** | Custom FastAPI (Python) | Receives tasks, calls AI API, dispatches tools |
| **n8n** | `n8nio/n8n` | Workflow engine: schedules, webhooks, service glue |
| **Postgres + pgvector** | `pgvector/pgvector` | Persistent memory, conversation history, vector search |
| **Playwright** | `mcr.microsoft.com/playwright/python` | Headless web browsing on behalf of agent |
| **Telegram Bot** | n8n workflow + webhook | Phone-based trigger interface |
| **Redis** | `redis:alpine` | Job queue between n8n and Agent Core |

---

## Service-by-Service Plan

### 1. Postgres + pgvector
- Single DB with schemas: `memory`, `conversations`, `tasks`
- `memory` table: stores facts, preferences, learned context as embeddings
- `conversations` table: full chat history per session
- pgvector extension for semantic similarity search on memory retrieval

### 2. Agent Core (Custom Python FastAPI)
This is the brain. It:
- Exposes a `/chat` REST endpoint (called by Open WebUI and n8n)
- Takes user message + session ID
- Retrieves relevant memories from Postgres via vector similarity
- Builds prompt with memory context + conversation history
- Calls OpenAI (GPT-4o) or Anthropic (Claude) with tool-calling enabled
- Dispatches tool calls to:
  - Playwright service (web browse/scrape)
  - n8n webhook triggers (for HA, Nextcloud, Gmail, etc.)
  - Direct API calls (Plex, Proxmox REST APIs)
  - Shell/file operations (sandboxed)
- Saves response + new memories back to Postgres

**Tools the agent will have:**
- `browse_web(url)` → Playwright
- `web_search(query)` → SearXNG or Brave Search API
- `send_email(to, subject, body)` → Gmail API via n8n
- `read_email(filter)` → Gmail API via n8n
- `control_home(entity, action)` → Home Assistant REST API
- `manage_files(action, path)` → Nextcloud WebDAV
- `run_script(code)` → sandboxed Python exec
- `query_memory(topic)` → pgvector similarity search
- `save_memory(fact)` → write to memory table
- `get_calendar(range)` → Google Calendar API via n8n
- `plex_control(action)` → Plex API
- `proxmox_action(action, vm)` → Proxmox REST API

### 3. n8n
- Acts as the glue layer for external services
- Workflows to build:
  - **Gmail read/send** — OAuth2 Gmail node
  - **Google Calendar** — read/create events
  - **Home Assistant webhook** — call HA REST API
  - **Telegram bot** — receive messages → call Agent Core → reply
  - **Scheduled jobs** — daily briefing, email digest, reminders
  - **Nextcloud** — file operations
- Agent Core calls n8n via webhook URLs to trigger these workflows
- n8n calls Agent Core `/chat` for AI reasoning within workflows

### 4. Open WebUI
- Configured to point at Agent Core `/chat` as a custom OpenAI-compatible backend
- Local-only access (no reverse proxy, LAN only)
- Used for desktop/browser interaction

### 5. Playwright
- Runs as a sidecar container with a simple HTTP API
- Agent Core sends `browse(url)` or `screenshot(url)` requests
- Returns page content as markdown/text for the agent to reason over

### 6. Telegram Bot
- Created via BotFather (one-time step)
- n8n Telegram Trigger node receives messages
- n8n calls Agent Core `/chat` with the message
- Reply sent back via Telegram Send node

---

## Directory Structure

```
~/personal-assistant/
├── docker-compose.yml
├── .env                        ← secrets (API keys, tokens)
├── agent-core/
│   ├── Dockerfile
│   ├── main.py                 ← FastAPI app
│   ├── tools/
│   │   ├── browser.py
│   │   ├── gmail.py
│   │   ├── home_assistant.py
│   │   ├── nextcloud.py
│   │   ├── plex.py
│   │   ├── proxmox.py
│   │   └── memory.py
│   ├── memory.py               ← pgvector read/write
│   ├── agent.py                ← LLM call + tool dispatch loop
│   └── requirements.txt
├── playwright-service/
│   ├── Dockerfile
│   └── server.py               ← simple HTTP wrapper around Playwright
├── n8n-data/                   ← n8n persistent volume
└── postgres-data/              ← postgres persistent volume
```

---

## .env Variables Needed (you will provide these)

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
HOME_ASSISTANT_URL=
HOME_ASSISTANT_TOKEN=
NEXTCLOUD_URL=
NEXTCLOUD_USER=
NEXTCLOUD_PASS=
PLEX_URL=
PLEX_TOKEN=
PROXMOX_URL=
PROXMOX_API_TOKEN=
POSTGRES_PASSWORD=
N8N_ENCRYPTION_KEY=
```

---

## Build Order (Implementation Phases)

1. **Phase 1 — Foundation**: `docker-compose.yml` with Postgres + pgvector, Redis, n8n, Open WebUI. Verify all containers start and can talk to each other.
2. **Phase 2 — Agent Core**: Build the FastAPI service with basic `/chat` endpoint, LLM call, conversation history in Postgres.
3. **Phase 3 — Memory**: Add pgvector memory layer — store/retrieve facts via embeddings. Wire into agent prompt building.
4. **Phase 4 — Tools**: Add tools one by one starting with web browse (Playwright), then home automation, then email/calendar.
5. **Phase 5 — n8n Workflows**: Build all n8n workflows. Wire Agent Core ↔ n8n webhooks. Set up scheduled jobs.
6. **Phase 6 — Telegram Bot**: Set up bot, wire through n8n to Agent Core.
7. **Phase 7 — Open WebUI**: Configure as the primary desktop chat interface.
8. **Phase 8 — Polish**: System prompt tuning, memory hygiene, error handling, health checks.

---

## Key Decisions & Tradeoffs

- **No OpenHands directly** — we build a leaner, purpose-built agent instead of using OpenHands as a base. This keeps it auditable, simple, and tailored to your use case.
- **n8n as service glue** — rather than writing native integrations for every service, n8n handles OAuth flows, retries, and scheduling. Agent Core just calls webhook URLs.
- **pgvector for memory** — avoids adding a separate vector DB (Chroma, Weaviate) by using Postgres with the pgvector extension. One less moving part.
- **Open WebUI as chat UI** — battle-tested, supports OpenAI-compatible API, no need to build a custom frontend.
- **LAN only** — no SSL cert, no reverse proxy needed for now. Access via `http://server-ip:3000`. Can add Caddy later if needed.
- **AI provider** — start with OpenAI GPT-4o for tool calling reliability. Anthropic Claude can be swapped in per-request.
