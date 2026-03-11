# 🤖 Personal AI Assistant

A self-hosted, privacy-first personal AI assistant stack built with Docker Compose. Runs entirely on your home server — no cloud required. Acts as your IT department, personal assistant, homelab manager, content creator, and digital life helper all in one.

Inspired by OpenHands/OpenDevin but built from scratch so you own every piece of it.

---

## What It Does

- **Chat with your assistant** via a clean web UI (Open WebUI) or Telegram
- **Manage your homelab** — monitor servers, update Docker containers, check for threats, manage Proxmox VMs
- **Control your smart home** via Home Assistant
- **Manage files** on Nextcloud
- **Control media** via Plex
- **Manage TrueNAS** storage — pools, datasets, alerts, scrub tasks
- **SSH into any Linux server or TrueNAS** and run commands, manage Docker, read logs
- **Security monitoring** — failed logins, open ports, auth logs, firewall status
- **Send and read Gmail** via n8n automation
- **Automate your YouTube channel** — research topics, write scripts, generate narration videos with AI images, upload with titles/descriptions/thumbnails
- **Persistent memory** — remembers facts about you and your preferences across sessions
- **Admin panel** — manage all integrations, API keys, SSH servers, and AI providers from a browser UI without touching server files
- **Multi-provider AI** — Abacus AI, OpenAI, Anthropic, or any local LLM (Ollama, LM Studio, vLLM)
- **n8n workflows** — Telegram bot, Gmail automation, daily briefing cron job, and more

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Your Home Server                      │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Open WebUI  │    │   Telegram   │    │  Admin Panel │  │
│  │  (port 3000) │    │   Bot (n8n)  │    │  (port 8000) │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │   Agent Core    │                      │
│                    │  FastAPI/Python │                      │
│                    │   (port 8000)   │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│        ┌────────────────────┼────────────────────┐         │
│        │                    │                    │          │
│  ┌─────▼──────┐   ┌─────────▼──────┐  ┌────────▼──────┐  │
│  │  Postgres  │   │     Redis      │  │   Playwright  │  │
│  │ (pgvector) │   │  (job queue)   │  │  (headless    │  │
│  │            │   │                │  │   browser)    │  │
│  └────────────┘   └────────────────┘  └───────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    n8n                              │   │
│  │  Gmail · Telegram Bot · Daily Briefing · Webhooks  │   │
│  │                  (port 5678)                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `agent-core` | Custom Python/FastAPI | 8000 | Main AI agent, REST API, tool execution |
| `postgres` | pgvector/pgvector:pg16 | internal | Persistent memory, conversation history, configs |
| `redis` | redis:7-alpine | internal | Job queue |
| `playwright` | Custom Python | internal | Headless browser for web tools |
| `n8n` | n8nio/n8n | 5678 | Workflow automation (Gmail, Telegram, cron) |
| `open-webui` | ghcr.io/open-webui/open-webui | 3000 | Chat web interface |

---

## Tools & Integrations

### Homelab & Infrastructure
| Tool | What It Does |
|---|---|
| `proxmox_action` | Manage VMs and containers — start, stop, snapshots, resource usage |
| `truenas_action` | TrueNAS storage — pools, datasets, alerts, services, disk stats, scrub |
| `ssh_exec` | Run any shell command on a registered Linux server or TrueNAS via SSH |
| `ssh_docker_action` | Docker management on remote servers — list, pull images, restart, logs, prune |
| `security_monitor` | Security checks — failed logins, open ports, auth logs, firewall, security updates |

### Smart Home & Media
| Tool | What It Does |
|---|---|
| `control_home` | Control Home Assistant devices and automations |
| `plex_control` | Control Plex media server |
| `manage_files` | Manage Nextcloud files (upload, download, list, delete) |

### Communication
| Tool | What It Does |
|---|---|
| `send_email` | Send Gmail via n8n OAuth2 |
| `read_email` | Read Gmail via n8n OAuth2 |

### Memory
| Tool | What It Does |
|---|---|
| `save_memory` | Save facts to persistent pgvector memory |
| `query_memory` | Semantic search across all stored memories |

### Web & Research
| Tool | What It Does |
|---|---|
| `browse_web` | Browse any URL with headless Playwright browser |

### YouTube & Content Creation
| Tool | What It Does |
|---|---|
| `youtube_research` | Research trending topics, search videos, keyword frequency |
| `youtube_write_script` | LLM-written script with hook, sections, CTA, title suggestions |
| `youtube_create_video` | Generate narration (edge-tts) + AI images (Stability AI) → assemble MP4 (MoviePy) |
| `youtube_generate_thumbnail` | Generate thumbnail via Stability AI or DALL-E 3 |
| `youtube_upload` | Upload video to YouTube with title, description, tags, thumbnail |

---

## AI Providers

You can switch between providers at any time from the admin panel — no server restart needed.

| Provider | Notes |
|---|---|
| **Abacus AI** | Default. Set `ABACUS_API_KEY` in `.env` |
| **OpenAI** | Set `OPENAI_API_KEY`. Uses GPT-4o by default |
| **Anthropic** | Set `ANTHROPIC_API_KEY`. Uses Claude 3.5 Sonnet |
| **Local LLM** | Ollama, LM Studio, or vLLM. Set `LOCAL_LLM_URL` |

---

## Quick Start

### Prerequisites
- Docker and Docker Compose installed on your home server
- (Optional) API keys for the services you want to use

### Install Docker (if needed)
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Deploy
```bash
git clone https://github.com/YOUR_USERNAME/personal-assistant.git
cd personal-assistant
cp .env.example .env
nano .env        # fill in your API keys and passwords
bash setup.sh    # builds containers, starts stack, imports n8n workflows
```

### Access
| Interface | URL |
|---|---|
| Chat (Open WebUI) | `http://your-server-ip:3000` |
| Admin Panel | `http://your-server-ip:8000/admin` |
| n8n Workflows | `http://your-server-ip:5678` |
| Agent API | `http://your-server-ip:8000` |

---

## Configuration

### Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in your values. The minimum required to get started:

```env
# Required
AGENT_SECRET_KEY=your-strong-secret-key-here
POSTGRES_PASSWORD=your-db-password
N8N_ENCRYPTION_KEY=your-n8n-encryption-key

# At least one AI provider
ABACUS_API_KEY=your-abacus-api-key
# or
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else (Home Assistant, Nextcloud, Plex, TrueNAS, SSH servers, YouTube, etc.) can be configured later from the admin panel at `http://your-server-ip:8000/admin`.

### Admin Panel

The admin panel lets you manage everything from a browser:

- **AI Providers** — add providers, set active provider, enter API keys
- **Homelab** — configure Proxmox, TrueNAS, Home Assistant
- **Storage** — configure Nextcloud
- **Media** — configure Plex
- **Comms** — configure Gmail, Telegram
- **Content/YouTube** — configure YouTube OAuth2, Stability AI, ElevenLabs, Runway ML
- **SSH Servers** — add Linux servers and TrueNAS with password or SSH key auth, test connections
- **Memory** — search and manually add memories
- **Sessions** — browse conversation history

### SSH Server Management

Add your servers in the admin panel under **SSH Servers**. Supports both password and private key authentication. The agent can then:

- Run any shell command on your servers
- List and manage Docker containers
- Pull image updates and restart containers
- Run security checks (failed logins, open ports, firewall status)
- Check for available security updates

### YouTube Automation

Full video pipeline from idea to upload:

1. Agent researches trending topics in your chosen genre
2. Writes a full script with hook, sections, and call-to-action
3. Generates TTS narration using `edge-tts` (free, no API key needed)
4. Generates section images using Stability AI (optional)
5. Assembles narration + images into an MP4 slideshow
6. Generates a thumbnail with Stability AI or DALL-E
7. Uploads to your YouTube channel with title, description, and tags

Configure YouTube credentials in the admin panel (requires a YouTube Data API v3 OAuth2 client ID, secret, and refresh token from Google Cloud Console).

---

## Project Structure

```
personal-assistant/
├── docker-compose.yml
├── .env.example
├── setup.sh                        # Bootstrap script
├── import-workflows.py             # n8n workflow importer
│
├── agent-core/                     # Main Python FastAPI service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app, all HTTP endpoints
│   ├── agent.py                    # Agent loop, tool dispatch
│   ├── memory.py                   # pgvector memory manager
│   ├── config.py                   # Pydantic settings
│   ├── admin_api.py                # Admin REST API router
│   ├── db/
│   │   └── init.sql                # Postgres schema + seed data
│   ├── providers/                  # AI provider implementations
│   │   ├── base.py
│   │   ├── abacus.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── local_provider.py
│   ├── tools/                      # Agent tool implementations
│   │   ├── browser.py
│   │   ├── home_assistant.py
│   │   ├── nextcloud.py
│   │   ├── plex.py
│   │   ├── proxmox.py
│   │   ├── truenas.py
│   │   ├── ssh_tool.py
│   │   ├── security.py
│   │   ├── gmail.py
│   │   ├── memory_tool.py
│   │   ├── youtube.py
│   │   └── __init__.py
│   └── static/
│       └── admin.html              # Single-page admin UI
│
├── playwright-service/             # Headless browser service
│   ├── Dockerfile
│   └── server.py
│
└── n8n-workflows/                  # Pre-built n8n automations
    ├── gmail-send.json
    ├── gmail-read.json
    ├── telegram-bot.json
    └── daily-briefing.json
```

---

## API Endpoints

The agent-core exposes a fully OpenAI-compatible API so it works with any OpenAI-compatible client (Open WebUI, Continue.dev, etc.).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat |
| `GET` | `/v1/models` | List available providers as models |
| `POST` | `/chat` | Native chat endpoint |
| `POST` | `/memory` | Add a memory |
| `GET` | `/memory/search?q=...` | Search memories |
| `GET` | `/sessions` | List conversation sessions |
| `GET` | `/sessions/{id}` | Get session history |
| `GET` | `/providers` | List configured AI providers |
| `GET` | `/admin` | Admin panel UI |
| `GET/POST` | `/admin/providers` | Manage AI providers |
| `GET/PATCH` | `/admin/integrations/{name}` | Manage integrations |
| `POST` | `/admin/integrations/{name}/test` | Test an integration |
| `GET/POST/PUT/DELETE` | `/admin/ssh-servers` | Manage SSH servers |
| `POST` | `/admin/ssh-servers/{id}/test` | Test SSH connection |

All endpoints except `/health` and `/admin` (UI only) require `Authorization: Bearer YOUR_AGENT_SECRET_KEY`.

---

## n8n Workflows

Pre-built workflows are automatically imported on first run by `setup.sh`:

| Workflow | Trigger | What It Does |
|---|---|---|
| `gmail-send.json` | Webhook from agent | Sends email via Gmail OAuth2 |
| `gmail-read.json` | Webhook from agent | Reads recent emails from Gmail |
| `telegram-bot.json` | Telegram message | Forwards message to agent, sends reply back |
| `daily-briefing.json` | 8:00 AM cron | Asks agent for a morning briefing, sends via Telegram |

To set up Telegram: create a bot via [@BotFather](https://t.me/BotFather), add the token to `.env` as `TELEGRAM_BOT_TOKEN`.

---

## Security Notes

- The stack is designed for **LAN-only access** — do not expose ports 3000, 5678, or 8000 directly to the internet
- All agent API endpoints are protected by `AGENT_SECRET_KEY`
- SSH credentials are stored encrypted in Postgres and never returned in API responses
- If you want remote access, put it behind a VPN (WireGuard/Tailscale) rather than a public reverse proxy

---

## License

MIT
