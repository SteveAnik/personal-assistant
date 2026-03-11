from memory import MemoryManager

SAVE_MEMORY_DEFINITION = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": "Save a fact or piece of information to long-term memory so you can recall it in future conversations.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The fact or information to remember"},
                "category": {"type": "string", "description": "Category tag e.g. preference, person, task, fact", "default": "general"},
                "importance": {"type": "number", "description": "Importance from 0.0 to 1.0", "default": 0.5},
            },
            "required": ["content"],
        },
    },
}

QUERY_MEMORY_DEFINITION = {
    "type": "function",
    "function": {
        "name": "query_memory",
        "description": "Search long-term memory for facts or information relevant to a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in memory"},
                "category": {"type": "string", "description": "Optional: filter by category"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 5},
            },
            "required": ["query"],
        },
    },
}


async def save_memory(memory_manager: MemoryManager, content: str, category: str = "general", importance: float = 0.5) -> str:
    mem_id = await memory_manager.save_memory(content, category=category, source="agent", importance=importance)
    return f"Memory saved (id: {mem_id}): {content[:100]}"


async def query_memory(memory_manager: MemoryManager, query: str, category: str = None, limit: int = 5) -> str:
    results = await memory_manager.search_memories(query, limit=limit, category=category)
    if not results:
        return "No relevant memories found."
    lines = []
    for r in results:
        score = r.get("similarity", 0)
        lines.append(f"[{r['category']}] (relevance: {score:.2f}) {r['content']}")
    return "\n".join(lines)
