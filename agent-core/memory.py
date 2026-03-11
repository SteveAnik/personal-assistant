import asyncpg
import json
from typing import Optional
from providers import get_embedding_provider


async def get_conn(database_url: str):
    return await asyncpg.connect(database_url)


class MemoryManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool = None

    async def init(self):
        self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def save_memory(self, content: str, category: str = "general", source: str = "user", importance: float = 0.5, metadata: dict = None) -> str:
        provider = get_embedding_provider()
        embedding = await provider.embed(content)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO memories (content, embedding, category, source, importance, metadata)
                   VALUES ($1, $2::vector, $3, $4, $5, $6)
                   RETURNING id""",
                content, embedding_str, category, source, importance,
                json.dumps(metadata or {})
            )
        return str(row["id"])

    async def search_memories(self, query: str, limit: int = 5, category: Optional[str] = None) -> list[dict]:
        provider = get_embedding_provider()
        embedding = await provider.embed(query)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        async with self._pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """SELECT id, content, category, source, importance, metadata, created_at,
                              1 - (embedding <=> $1::vector) AS similarity
                       FROM memories
                       WHERE category = $2
                       ORDER BY embedding <=> $1::vector
                       LIMIT $3""",
                    embedding_str, category, limit
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, content, category, source, importance, metadata, created_at,
                              1 - (embedding <=> $1::vector) AS similarity
                       FROM memories
                       ORDER BY embedding <=> $1::vector
                       LIMIT $2""",
                    embedding_str, limit
                )
        return [dict(r) for r in rows]

    async def save_conversation(self, session_id: str, role: str, content: str, tool_calls=None, tool_call_id: str = None, metadata: dict = None):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO conversations (session_id, role, content, tool_calls, tool_call_id, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                session_id, role, content,
                json.dumps(tool_calls) if tool_calls else None,
                tool_call_id,
                json.dumps(metadata or {})
            )

    async def get_conversation(self, session_id: str, limit: int = 40) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT role, content, tool_calls, tool_call_id
                   FROM conversations
                   WHERE session_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2""",
                session_id, limit
            )
        return list(reversed([dict(r) for r in rows]))

    async def list_sessions(self) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT session_id, MAX(created_at) as last_active
                   FROM conversations GROUP BY session_id ORDER BY last_active DESC LIMIT 50"""
            )
        return [r["session_id"] for r in rows]
