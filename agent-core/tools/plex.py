import httpx
from config import settings

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "plex_control",
        "description": "Control Plex media server. Search for media, get what's playing, control playback.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search", "now_playing", "libraries", "recently_added"], "description": "Action to perform"},
                "query": {"type": "string", "description": "Search query (for search action)"},
            },
            "required": ["action"],
        },
    },
}


async def plex_control(action: str, query: str = None) -> str:
    if not settings.plex_url or not settings.plex_token:
        return "Plex is not configured. Set PLEX_URL and PLEX_TOKEN in .env"

    base = settings.plex_url.rstrip("/")
    headers = {"X-Plex-Token": settings.plex_token, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            if action == "libraries":
                resp = await client.get(f"{base}/library/sections", headers=headers)
                resp.raise_for_status()
                libs = resp.json()["MediaContainer"]["Directory"]
                return "\n".join(f"- {l['title']} ({l['type']})" for l in libs)
            elif action == "now_playing":
                resp = await client.get(f"{base}/status/sessions", headers=headers)
                resp.raise_for_status()
                data = resp.json()["MediaContainer"]
                if not data.get("size"):
                    return "Nothing is currently playing."
                sessions = data.get("Metadata", [])
                return "\n".join(f"- {s.get('title')} [{s.get('type')}] - {s.get('Player', {}).get('title', 'unknown device')}" for s in sessions)
            elif action == "recently_added":
                resp = await client.get(f"{base}/library/recentlyAdded", headers=headers)
                resp.raise_for_status()
                items = resp.json()["MediaContainer"].get("Metadata", [])[:10]
                return "\n".join(f"- {i.get('title')} ({i.get('year', '')})" for i in items)
            elif action == "search" and query:
                resp = await client.get(f"{base}/search", headers=headers, params={"query": query})
                resp.raise_for_status()
                items = resp.json()["MediaContainer"].get("Metadata", [])[:10]
                if not items:
                    return f"No results found for '{query}'"
                return "\n".join(f"- {i.get('title')} ({i.get('type')}, {i.get('year', '')})" for i in items)
    except Exception as e:
        return f"Plex error: {e}"
