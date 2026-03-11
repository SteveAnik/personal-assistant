from .base import BaseProvider, Message, LLMResponse, ToolCall
from .abacus import AbacusProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .local_provider import LocalProvider
from config import settings

_registry: dict[str, BaseProvider] = {
    "abacus": AbacusProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "local": LocalProvider(),
}


def get_provider(name: str | None = None) -> BaseProvider:
    key = (name or settings.active_provider).lower()
    provider = _registry.get(key)
    if not provider:
        raise ValueError(f"Unknown provider: {key}. Valid options: {list(_registry.keys())}")
    if not provider.is_configured():
        raise ValueError(f"Provider '{key}' is not configured. Check your .env file.")
    return provider


def get_embedding_provider() -> BaseProvider:
    return get_provider(settings.embedding_provider)


def list_providers() -> list[dict]:
    return [
        {
            "name": k,
            "configured": v.is_configured(),
            "active": k == settings.active_provider,
        }
        for k, v in _registry.items()
    ]


__all__ = ["get_provider", "get_embedding_provider", "list_providers", "Message", "LLMResponse", "ToolCall"]
