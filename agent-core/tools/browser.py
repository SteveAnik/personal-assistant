import httpx
from config import settings

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "browse_web",
        "description": "Browse a URL and return the page content as text. Use this to read articles, documentation, or any web page.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to browse"},
                "extract": {"type": "string", "enum": ["text", "markdown", "links"], "description": "What to extract from the page", "default": "markdown"},
            },
            "required": ["url"],
        },
    },
}


async def browse_web(url: str, extract: str = "markdown") -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.playwright_url}/browse",
                json={"url": url, "extract": extract},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("content", "No content returned")
    except Exception as e:
        return f"Error browsing {url}: {e}"
