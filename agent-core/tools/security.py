from .ssh_tool import ssh_exec

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "security_monitor",
        "description": "Monitor security on a remote server: check failed login attempts, open ports, suspicious processes, recent auth logs, firewall status, and package security updates",
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "UUID or name label of the SSH server"},
                "check": {
                    "type": "string",
                    "enum": [
                        "failed_logins",
                        "open_ports",
                        "suspicious_processes",
                        "auth_log",
                        "firewall_status",
                        "security_updates",
                        "last_logins",
                        "cron_jobs",
                        "suid_files",
                        "full_report",
                    ],
                    "description": "Security check to perform",
                },
                "lines": {"type": "integer", "description": "Number of log lines to return (default 50)", "default": 50},
            },
            "required": ["server_id", "check"],
        },
    },
}

_COMMANDS = {
    "failed_logins": "grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -{lines} || grep 'Failed password' /var/log/secure 2>/dev/null | tail -{lines}",
    "open_ports": "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",
    "suspicious_processes": "ps aux --sort=-%cpu | head -20",
    "auth_log": "tail -{lines} /var/log/auth.log 2>/dev/null || tail -{lines} /var/log/secure 2>/dev/null",
    "firewall_status": "ufw status verbose 2>/dev/null || iptables -L -n --line-numbers 2>/dev/null | head -60",
    "security_updates": "apt list --upgradable 2>/dev/null | grep -i security | head -30 || yum check-update --security 2>/dev/null | head -30",
    "last_logins": "last -n 20",
    "cron_jobs": "for u in $(cut -f1 -d: /etc/passwd); do crontab -u $u -l 2>/dev/null | grep -v '^#' | grep -v '^$' | sed \"s/^/$u: /\"; done",
    "suid_files": "find / -perm -4000 -type f 2>/dev/null | head -30",
    "full_report": (
        "echo '=== FAILED LOGINS ===' && grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -10 && "
        "echo '=== OPEN PORTS ===' && ss -tlnp 2>/dev/null | head -20 && "
        "echo '=== LAST LOGINS ===' && last -n 10 && "
        "echo '=== TOP PROCESSES ===' && ps aux --sort=-%cpu | head -10 && "
        "echo '=== FIREWALL ===' && ufw status 2>/dev/null || echo 'ufw not available' && "
        "echo '=== DISK USAGE ===' && df -h && "
        "echo '=== MEMORY ===' && free -h"
    ),
}


async def security_monitor(db_pool, server_id: str, check: str, lines: int = 50) -> dict:
    template = _COMMANDS.get(check)
    if not template:
        return {"error": f"Unknown check: {check}"}
    command = template.replace("{lines}", str(lines))
    result = await ssh_exec(db_pool, server_id, command, timeout=30)
    return {"check": check, "server": server_id, **result}
