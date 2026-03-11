import json
from typing import Optional
from anthropic import AsyncAnthropic
from .base import BaseProvider, Message, LLMResponse, ToolCall
from config import settings


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self._client = None

    def _get_client(self) -> AsyncAnthropic:
        if not self._client:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _convert_messages(self, messages: list[Message]):
        system = None
        converted = []
        for m in messages:
            if m.role == "system":
                system = m.content
                continue
            msg: dict = {"role": m.role}
            if m.tool_call_id:
                msg["role"] = "user"
                msg["content"] = [{"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content or ""}]
            elif m.tool_calls:
                blocks = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": json.loads(tc["function"]["arguments"])})
                msg["content"] = blocks
            else:
                msg["content"] = m.content or ""
            converted.append(msg)
        return system, converted

    async def chat(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        system, converted = self._convert_messages(messages)

        anthropic_tools = []
        if tools:
            for t in tools:
                fn = t.get("function", t)
                anthropic_tools.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })

        kwargs: dict = {
            "model": self.model,
            "messages": converted,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        resp = await client.messages.create(**kwargs)

        content = None
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=resp.model,
            usage={"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
            finish_reason=resp.stop_reason or "stop",
        )

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Anthropic does not provide an embeddings API. Set EMBEDDING_PROVIDER=openai or abacus.")
