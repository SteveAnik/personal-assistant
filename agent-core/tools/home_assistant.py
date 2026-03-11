import httpx
from config import settings

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "control_home",
        "description": "Control a Home Assistant entity. Turn lights on/off, set thermostat, check sensor state, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "The Home Assistant entity ID, e.g. light.living_room"},
                "action": {"type": "string", "enum": ["turn_on", "turn_off", "toggle", "get_state"], "description": "Action to perform"},
                "attributes": {"type": "object", "description": "Optional attributes like brightness, temperature", "default": {}},
            },
            "required": ["entity_id", "action"],
        },
    },
}


async def control_home(entity_id: str, action: str, attributes: dict = None) -> str:
    if not settings.home_assistant_url or not settings.home_assistant_token:
        return "Home Assistant is not configured. Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in .env"

    headers = {
        "Authorization": f"Bearer {settings.home_assistant_token}",
        "Content-Type": "application/json",
    }
    base = settings.home_assistant_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            if action == "get_state":
                resp = await client.get(f"{base}/api/states/{entity_id}", headers=headers)
                resp.raise_for_status()
                state = resp.json()
                return f"Entity {entity_id}: state={state.get('state')}, attributes={state.get('attributes', {})}"
            else:
                domain = entity_id.split(".")[0]
                payload = {"entity_id": entity_id}
                if attributes:
                    payload.update(attributes)
                resp = await client.post(f"{base}/api/services/{domain}/{action}", headers=headers, json=payload)
                resp.raise_for_status()
                return f"Successfully called {action} on {entity_id}"
    except Exception as e:
        return f"Home Assistant error: {e}"
