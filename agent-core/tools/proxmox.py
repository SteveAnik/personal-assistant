import httpx
from config import settings

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "proxmox_action",
        "description": "Manage Proxmox VMs and containers. List, start, stop, get status.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list_nodes", "list_vms", "get_status", "start", "stop", "reboot"], "description": "Action to perform"},
                "node": {"type": "string", "description": "Proxmox node name (required for VM actions)"},
                "vmid": {"type": "integer", "description": "VM/container ID (required for start/stop/status)"},
            },
            "required": ["action"],
        },
    },
}


async def proxmox_action(action: str, node: str = None, vmid: int = None) -> str:
    if not settings.proxmox_url or not settings.proxmox_api_token:
        return "Proxmox is not configured. Set PROXMOX_URL and PROXMOX_API_TOKEN in .env"

    base = settings.proxmox_url.rstrip("/")
    headers = {"Authorization": f"PVEAPIToken={settings.proxmox_api_token}"}

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            if action == "list_nodes":
                resp = await client.get(f"{base}/api2/json/nodes", headers=headers)
                resp.raise_for_status()
                nodes = resp.json()["data"]
                return "\n".join(f"- {n['node']} (status: {n['status']}, cpu: {n.get('cpu', 0):.1%})" for n in nodes)
            elif action == "list_vms":
                target = f"{base}/api2/json/nodes/{node}/qemu" if node else f"{base}/api2/json/cluster/resources?type=vm"
                resp = await client.get(target, headers=headers)
                resp.raise_for_status()
                vms = resp.json()["data"]
                return "\n".join(f"- [{v['vmid']}] {v.get('name', 'unnamed')} (status: {v['status']})" for v in vms)
            elif action in ("start", "stop", "reboot"):
                if not node or not vmid:
                    return "node and vmid are required for start/stop/reboot"
                resp = await client.post(f"{base}/api2/json/nodes/{node}/qemu/{vmid}/status/{action}", headers=headers)
                resp.raise_for_status()
                return f"VM {vmid} on node {node}: {action} initiated"
            elif action == "get_status":
                if not node or not vmid:
                    return "node and vmid are required for get_status"
                resp = await client.get(f"{base}/api2/json/nodes/{node}/qemu/{vmid}/status/current", headers=headers)
                resp.raise_for_status()
                d = resp.json()["data"]
                return f"VM {vmid}: status={d['status']}, cpu={d.get('cpu', 0):.1%}, mem={d.get('mem', 0) // 1024 // 1024}MB"
    except Exception as e:
        return f"Proxmox error: {e}"
