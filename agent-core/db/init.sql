CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS n8n;

-- ── Conversations ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_call_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, created_at);

-- ── Memory ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    embedding vector(1536),
    category TEXT DEFAULT 'general',
    source TEXT DEFAULT 'user',
    importance FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);

-- ── Tasks ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'done', 'failed')),
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── AI Provider configs ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL,
    api_key TEXT,
    api_url TEXT,
    model TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Integrations ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    label TEXT NOT NULL,
    url TEXT,
    api_key TEXT,
    username TEXT,
    password TEXT,
    extra JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT FALSE,
    last_tested_at TIMESTAMPTZ,
    last_test_ok BOOLEAN,
    last_test_msg TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO integrations (name, category, label, enabled) VALUES
  ('home_assistant', 'homelab',  'Home Assistant',  FALSE),
  ('nextcloud',      'storage',  'Nextcloud',       FALSE),
  ('plex',           'media',    'Plex',            FALSE),
  ('jellyfin',       'media',    'Jellyfin',        FALSE),
  ('proxmox',        'homelab',  'Proxmox',         FALSE),
  ('truenas',        'homelab',  'TrueNAS',         FALSE),
  ('gmail',          'comms',    'Gmail (n8n)',      FALSE),
  ('telegram',       'comms',    'Telegram Bot',    FALSE),
  ('youtube',        'content',  'YouTube',         FALSE),
  ('elevenlabs',     'content',  'ElevenLabs TTS',  FALSE),
  ('stability',      'content',  'Stability AI',    FALSE),
  ('runwayml',       'content',  'Runway ML',       FALSE),
  ('canva',          'content',  'Canva',           FALSE),
  ('capcut',         'content',  'CapCut',          FALSE)
ON CONFLICT (name) DO NOTHING;

-- ── SSH Servers ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ssh_servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    host TEXT NOT NULL,
    port INTEGER DEFAULT 22,
    username TEXT NOT NULL,
    auth_type TEXT DEFAULT 'password' CHECK (auth_type IN ('password', 'key')),
    password TEXT,
    private_key TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
