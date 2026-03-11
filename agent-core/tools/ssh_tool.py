import asyncssh
from typing import Any

EXEC_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "ssh_exec",
        "description": "Execute a shell command on a registered SSH server (Linux server or TrueNAS). Use for monitoring, docker updates, log checks, and system administration.",
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "UUID or name label of the SSH server from the admin panel"},
                "command": {"type": "string", "description": "Shell command to run on the remote server"},
                "timeout": {"type": "integer", "description": "Command timeout in seconds (default 30)", "default": 30},
            },
            "required": ["server_id", "command"],
        },
    },
}

DOCKER_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "ssh_docker_action",
        "description": "Perform Docker operations on a remote server via SSH: list containers, check updates, pull images, restart containers, view logs",
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "UUID or name label of the SSH server"},
                "action": {
                    "type": "string",
                    "enum": ["list_containers", "check_updates", "pull_image", "restart_container", "stop_container", "start_container", "get_logs", "system_prune"],
                    "description": "Docker action to perform",
                },
                "container_name": {"type": "string", "description": "Container name or ID (for restart/stop/start/logs/pull)"},
                "image": {"type": "string", "description": "Image name for pull action"},
                "tail_lines": {"type": "integer", "description": "Number of log lines to return (default 50)", "default": 50},
            },
            "required": ["server_id", "action"],
        },
    },
}


async def _get_server(db_pool, server_id: str) -> dict | None:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM ssh_servers WHERE id::text = $1 OR name = $1",
            server_id
        )
        return dict(row) if row else None


async def _connect(server: dict):
    kwargs: dict = {
        "host": server["host"],
        "port": server.get("port", 22),
        "username": server["username"],
        "known_hosts": None,
    }
    if server.get("auth_type") == "key" and server.get("private_key"):
        kwargs["client_keys"] = [asyncssh.import_private_key(server["private_key"])]
    else:
        kwargs["password"] = server.get("password", "")
    return await asyncssh.connect(**kwargs)


async def ssh_exec(db_pool, server_id: str, command: str, timeout: int = 30) -> dict:
    server = await _get_server(db_pool, server_id)
    if not server:
        return {"error": f"SSH server '{server_id}' not found. Add it in the admin panel under SSH Servers."}
    try:
        async with await _connect(server) as conn:
            result = await asyncio.wait_for(
                conn.run(command, check=False),
                timeout=timeout
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.exit_status,
            }
    except Exception as e:
        return {"error": str(e)}


async def ssh_docker_action(db_pool, server_id: str, action: str, **kwargs: Any) -> dict:
    container = kwargs.get("container_name", "")
    image = kwargs.get("image", "")
    tail = kwargs.get("tail_lines", 50)

    commands = {
        "list_containers": "docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'",
        "check_updates": "docker images --format '{{.Repository}}:{{.Tag}}' | head -50",
        "pull_image": f"docker pull {image or container}",
        "restart_container": f"docker restart {container}",
        "stop_container": f"docker stop {container}",
        "start_container": f"docker start {container}",
        "get_logs": f"docker logs --tail {tail} {container}",
        "system_prune": "docker system prune -f",
    }

    if action not in commands:
        return {"error": f"Unknown action: {action}"}

    cmd = commands[action]
    return await ssh_exec(db_pool, server_id, cmd, timeout=60)


import asyncio
