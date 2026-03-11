import httpx
from typing import Any

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "truenas_action",
        "description": "Interact with TrueNAS storage server: check pools, datasets, services, jails, alerts, and system info",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get_system_info",
                        "list_pools",
                        "list_datasets",
                        "get_alerts",
                        "list_services",
                        "start_service",
                        "stop_service",
                        "list_jails",
                        "get_disk_stats",
                        "get_replication_tasks",
                        "run_scrub",
                    ],
                    "description": "The TrueNAS action to perform",
                },
                "service_name": {"type": "string", "description": "Service name for start/stop actions"},
                "pool_name": {"type": "string", "description": "Pool name for scrub action"},
            },
            "required": ["action"],
        },
    },
}


async def truenas_action(config: dict, action: str, **kwargs: Any) -> dict:
    url = config.get("url", "").rstrip("/")
    api_key = config.get("api_key", "")
    if not url or not api_key:
        return {"error": "TrueNAS not configured. Set URL and API key in admin panel."}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    base = f"{url}/api/v2.0"

    async with httpx.AsyncClient(verify=False, timeout=20) as client:
        try:
            if action == "get_system_info":
                r = await client.get(f"{base}/system/info", headers=headers)
                return r.json()

            elif action == "list_pools":
                r = await client.get(f"{base}/pool", headers=headers)
                pools = r.json()
                return [{"name": p["name"], "status": p["status"], "size": p.get("size"), "free": p.get("free")} for p in pools]

            elif action == "list_datasets":
                r = await client.get(f"{base}/pool/dataset", headers=headers)
                datasets = r.json()
                return [{"name": d["name"], "type": d["type"], "used": d.get("used", {}).get("rawvalue"), "available": d.get("available", {}).get("rawvalue")} for d in datasets[:30]]

            elif action == "get_alerts":
                r = await client.get(f"{base}/alert/list", headers=headers)
                alerts = r.json()
                return [{"level": a["level"], "text": a["formatted"], "dismissed": a["dismissed"]} for a in alerts]

            elif action == "list_services":
                r = await client.get(f"{base}/service", headers=headers)
                services = r.json()
                return [{"service": s["service"], "state": s["state"], "enable": s["enable"]} for s in services]

            elif action == "start_service":
                svc = kwargs.get("service_name")
                r = await client.post(f"{base}/service/start", headers=headers, json={"service": svc})
                return {"result": r.json()}

            elif action == "stop_service":
                svc = kwargs.get("service_name")
                r = await client.post(f"{base}/service/stop", headers=headers, json={"service": svc})
                return {"result": r.json()}

            elif action == "list_jails":
                r = await client.get(f"{base}/jail", headers=headers)
                return r.json()

            elif action == "get_disk_stats":
                r = await client.get(f"{base}/disk", headers=headers)
                disks = r.json()
                return [{"name": d["name"], "size": d.get("size"), "serial": d.get("serial"), "temp": d.get("hddstandby")} for d in disks]

            elif action == "get_replication_tasks":
                r = await client.get(f"{base}/replication", headers=headers)
                return r.json()

            elif action == "run_scrub":
                pool = kwargs.get("pool_name")
                r = await client.post(f"{base}/pool/scrub", headers=headers, json={"name": pool, "threshold": 0})
                return {"result": r.json()}

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            return {"error": str(e)}
