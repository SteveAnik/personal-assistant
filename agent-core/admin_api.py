import json
import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import asyncssh

router = APIRouter(prefix="/admin", tags=["admin"])

_pool = None

async def get_pool(database_url: str):
    global _pool
    if not _pool:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return _pool


# ── Providers ──────────────────────────────────────────────────────────────────
class ProviderBody(BaseModel):
    name: str
    provider_type: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model: Optional[str] = None
    is_default: bool = False


class SetActiveBody(BaseModel):
    name: str


def make_router(database_url: str):
    r = APIRouter(prefix="/admin", tags=["admin"])

    async def pool():
        return await get_pool(database_url)

    # ── Providers ──────────────────────────────────────────────────────────────
    @r.get("/providers")
    async def list_db_providers():
        db = await pool()
        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM provider_configs ORDER BY created_at")
        return {"providers": [dict(r) for r in rows]}

    @r.post("/providers")
    async def upsert_provider(body: ProviderBody):
        db = await pool()
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO provider_configs (name, provider_type, api_key, api_url, model, is_default)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (name) DO UPDATE SET
                  provider_type=EXCLUDED.provider_type, api_key=EXCLUDED.api_key,
                  api_url=EXCLUDED.api_url, model=EXCLUDED.model,
                  is_default=EXCLUDED.is_default, updated_at=NOW()
            """, body.name, body.provider_type, body.api_key, body.api_url, body.model, body.is_default)
        return {"status": "saved"}

    @r.post("/providers/set-active")
    async def set_active_provider(body: SetActiveBody):
        db = await pool()
        async with db.acquire() as conn:
            await conn.execute("UPDATE provider_configs SET is_active=FALSE")
            await conn.execute("UPDATE provider_configs SET is_active=TRUE WHERE name=$1", body.name)
        return {"status": "ok", "active": body.name}

    # ── Integrations ───────────────────────────────────────────────────────────
    @r.get("/integrations")
    async def list_integrations():
        db = await pool()
        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM integrations ORDER BY category, name")
        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("extra"), str):
                d["extra"] = json.loads(d["extra"])
            result.append(d)
        return result

    @r.get("/integrations/{name}")
    async def get_integration(name: str):
        db = await pool()
        async with db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM integrations WHERE name=$1", name)
        if not row:
            raise HTTPException(404, "Integration not found")
        d = dict(row)
        if isinstance(d.get("extra"), str):
            d["extra"] = json.loads(d["extra"])
        return d

    @r.patch("/integrations/{name}")
    async def update_integration(name: str, body: dict):
        db = await pool()
        fields = []
        vals = []
        i = 1
        for k, v in body.items():
            if k in ("id","name","created_at","last_tested_at","last_test_ok","last_test_msg"):
                continue
            if k == "extra" and isinstance(v, dict):
                v = json.dumps(v)
            fields.append(f"{k}=${i}")
            vals.append(v)
            i += 1
        if not fields:
            return {"status": "nothing to update"}
        fields.append(f"updated_at=NOW()")
        vals.append(name)
        async with db.acquire() as conn:
            await conn.execute(f"UPDATE integrations SET {', '.join(fields)} WHERE name=${i}", *vals)
        return {"status": "saved"}

    @r.post("/integrations/{name}/test")
    async def test_integration(name: str):
        db = await pool()
        async with db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM integrations WHERE name=$1", name)
        if not row:
            raise HTTPException(404)
        d = dict(row)
        ok, msg = await _test_integration(name, d)
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE integrations SET last_tested_at=NOW(), last_test_ok=$1, last_test_msg=$2 WHERE name=$3",
                ok, msg, name
            )
        return {"ok": ok, "message": msg}

    # ── SSH Servers ────────────────────────────────────────────────────────────
    @r.get("/ssh-servers")
    async def list_ssh_servers():
        db = await pool()
        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT id, name, host, port, username, auth_type, enabled, created_at FROM ssh_servers ORDER BY name")
        return [dict(r) for r in rows]

    @r.get("/ssh-servers/{server_id}")
    async def get_ssh_server(server_id: str):
        db = await pool()
        async with db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM ssh_servers WHERE id=$1::uuid", server_id)
        if not row:
            raise HTTPException(404)
        return dict(row)

    @r.post("/ssh-servers")
    async def create_ssh_server(body: dict):
        db = await pool()
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO ssh_servers (name, host, port, username, auth_type, password, private_key, enabled)
                VALUES ($1,$2,$3,$4,$5,$6,$7,TRUE) RETURNING id
            """, body["name"], body["host"], int(body.get("port",22)), body["username"],
               body.get("auth_type","password"), body.get("password"), body.get("private_key"))
        return {"id": str(row["id"]), "status": "created"}

    @r.put("/ssh-servers/{server_id}")
    async def update_ssh_server(server_id: str, body: dict):
        db = await pool()
        async with db.acquire() as conn:
            await conn.execute("""
                UPDATE ssh_servers SET name=$1, host=$2, port=$3, username=$4,
                  auth_type=$5, password=$6, private_key=$7, updated_at=NOW()
                WHERE id=$8::uuid
            """, body["name"], body["host"], int(body.get("port",22)), body["username"],
               body.get("auth_type","password"), body.get("password"), body.get("private_key"), server_id)
        return {"status": "updated"}

    @r.delete("/ssh-servers/{server_id}")
    async def delete_ssh_server(server_id: str):
        db = await pool()
        async with db.acquire() as conn:
            await conn.execute("DELETE FROM ssh_servers WHERE id=$1::uuid", server_id)
        return {"status": "deleted"}

    @r.post("/ssh-servers/{server_id}/test")
    async def test_ssh_server(server_id: str):
        db = await pool()
        async with db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM ssh_servers WHERE id=$1::uuid", server_id)
        if not row:
            raise HTTPException(404)
        s = dict(row)
        try:
            kwargs = dict(host=s["host"], port=s["port"], username=s["username"], known_hosts=None)
            if s["auth_type"] == "key" and s.get("private_key"):
                kwargs["client_keys"] = [asyncssh.import_private_key(s["private_key"])]
            else:
                kwargs["password"] = s.get("password","")
            async with asyncssh.connect(**kwargs) as conn:
                result = await conn.run("echo ok", check=True)
            return {"ok": True, "message": f"Connected to {s['host']} as {s['username']}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    return r


# ── Integration test helpers ───────────────────────────────────────────────────
async def _test_integration(name: str, d: dict) -> tuple[bool, str]:
    url = d.get("url","").rstrip("/")
    key = d.get("api_key","")
    try:
        if name == "home_assistant":
            async with httpx.AsyncClient(timeout=8, verify=False) as c:
                r = await c.get(f"{url}/api/", headers={"Authorization": f"Bearer {key}"})
            return r.status_code == 200, f"HA responded: {r.status_code}"
        elif name == "proxmox":
            async with httpx.AsyncClient(timeout=8, verify=False) as c:
                r = await c.get(f"{url}/api2/json/nodes", headers={"Authorization": f"PVEAPIToken={key}"})
            return r.status_code == 200, f"Proxmox responded: {r.status_code}"
        elif name == "truenas":
            async with httpx.AsyncClient(timeout=8, verify=False) as c:
                r = await c.get(f"{url}/api/v2.0/system/info", headers={"Authorization": f"Bearer {key}"})
            return r.status_code == 200, f"TrueNAS responded: {r.status_code}"
        elif name == "plex":
            async with httpx.AsyncClient(timeout=8, verify=False) as c:
                r = await c.get(f"{url}/identity", params={"X-Plex-Token": key})
            return r.status_code == 200, f"Plex responded: {r.status_code}"
        elif name == "nextcloud":
            user = d.get("username","")
            pw = d.get("password","")
            async with httpx.AsyncClient(timeout=8, verify=False) as c:
                r = await c.get(f"{url}/ocs/v1.php/cloud/capabilities", auth=(user, pw))
            return r.status_code == 200, f"Nextcloud responded: {r.status_code}"
        elif name == "elevenlabs":
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": key})
            return r.status_code == 200, f"ElevenLabs: {r.status_code}"
        elif name == "stability":
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get("https://api.stability.ai/v1/user/account", headers={"Authorization": f"Bearer {key}"})
            return r.status_code == 200, f"Stability AI: {r.status_code}"
        elif name in ("gmail","telegram","youtube","runwayml"):
            return True, "Manual verification required — check n8n / external service."
        else:
            return False, "No test available for this integration."
    except Exception as e:
        return False, str(e)
