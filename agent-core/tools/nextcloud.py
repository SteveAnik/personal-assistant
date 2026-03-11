import httpx
from config import settings

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "manage_files",
        "description": "Manage files on Nextcloud. List, upload, download, or delete files.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "read", "upload", "delete", "create_folder"], "description": "File action to perform"},
                "path": {"type": "string", "description": "Remote path on Nextcloud, e.g. /Documents/notes.txt"},
                "content": {"type": "string", "description": "File content for upload action"},
            },
            "required": ["action", "path"],
        },
    },
}


async def manage_files(action: str, path: str, content: str = None) -> str:
    if not settings.nextcloud_url or not settings.nextcloud_user:
        return "Nextcloud is not configured. Set NEXTCLOUD_URL, NEXTCLOUD_USER, NEXTCLOUD_PASS in .env"

    base = settings.nextcloud_url.rstrip("/")
    dav_url = f"{base}/remote.php/dav/files/{settings.nextcloud_user}{path}"
    auth = (settings.nextcloud_user, settings.nextcloud_pass)

    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            if action == "list":
                resp = await client.request("PROPFIND", dav_url, auth=auth, headers={"Depth": "1"})
                resp.raise_for_status()
                return f"Directory listing (XML):\n{resp.text[:2000]}"
            elif action == "read":
                resp = await client.get(dav_url, auth=auth)
                resp.raise_for_status()
                return resp.text[:4000]
            elif action == "upload":
                resp = await client.put(dav_url, auth=auth, content=(content or "").encode())
                resp.raise_for_status()
                return f"Uploaded to {path}"
            elif action == "delete":
                resp = await client.delete(dav_url, auth=auth)
                resp.raise_for_status()
                return f"Deleted {path}"
            elif action == "create_folder":
                resp = await client.request("MKCOL", dav_url, auth=auth)
                resp.raise_for_status()
                return f"Created folder {path}"
    except Exception as e:
        return f"Nextcloud error: {e}"
