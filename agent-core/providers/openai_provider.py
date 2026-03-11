import json
from typing import Optional
from openai import AsyncOpenAI
from .base import BaseProvider, Message, LLMResponse, ToolCall
from config import settings


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self._client = None

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _messages_to_dict(self, messages: list[Message]) -> list[dict]:
        result = []
        for m in messages:
            msg: dict = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            result.append(msg)
        return result

    async def chat(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        kwargs: dict = {
            "model": self.model,
            "messages": self._messages_to_dict(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=resp.model,
            usage=resp.usage.model_dump() if resp.usage else {},
            finish_reason=choice.finish_reason or "stop",
        )

    async def embed(self, text: str) -> list[float]:
        client = self._get_client()
        resp = await client.embeddings.create(model=settings.embedding_model, input=text)
        return resp.data[0].embedding
