from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    active_provider: str = Field(default="abacus", env="ACTIVE_PROVIDER")

    abacus_api_key: Optional[str] = Field(default=None, env="ABACUS_API_KEY")
    abacus_api_url: str = Field(default="https://api.abacus.ai/api/v0", env="ABACUS_API_URL")
    abacus_model: str = Field(default="claude-sonnet-4-5", env="ABACUS_MODEL")

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")

    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-opus-4-5", env="ANTHROPIC_MODEL")

    local_llm_url: str = Field(default="http://ollama:11434/v1", env="LOCAL_LLM_URL")
    local_llm_model: str = Field(default="llama3", env="LOCAL_LLM_MODEL")

    embedding_provider: str = Field(default="abacus", env="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")

    database_url: str = Field(env="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")

    playwright_url: str = Field(default="http://playwright:3001", env="PLAYWRIGHT_URL")
    n8n_webhook_base_url: str = Field(default="http://n8n:5678", env="N8N_WEBHOOK_BASE_URL")

    agent_secret_key: str = Field(default="changeme", env="AGENT_SECRET_KEY")

    home_assistant_url: Optional[str] = Field(default=None, env="HOME_ASSISTANT_URL")
    home_assistant_token: Optional[str] = Field(default=None, env="HOME_ASSISTANT_TOKEN")

    nextcloud_url: Optional[str] = Field(default=None, env="NEXTCLOUD_URL")
    nextcloud_user: Optional[str] = Field(default=None, env="NEXTCLOUD_USER")
    nextcloud_pass: Optional[str] = Field(default=None, env="NEXTCLOUD_PASS")

    plex_url: Optional[str] = Field(default=None, env="PLEX_URL")
    plex_token: Optional[str] = Field(default=None, env="PLEX_TOKEN")

    proxmox_url: Optional[str] = Field(default=None, env="PROXMOX_URL")
    proxmox_api_token: Optional[str] = Field(default=None, env="PROXMOX_API_TOKEN")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
