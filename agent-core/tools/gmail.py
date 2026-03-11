import httpx
from config import settings

SEND_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Send an email via Gmail through n8n workflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body (plain text or HTML)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
}

READ_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_email",
        "description": "Read recent emails from Gmail via n8n workflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "Gmail search filter e.g. 'is:unread', 'from:boss@example.com'", "default": "is:unread"},
                "limit": {"type": "integer", "description": "Number of emails to retrieve", "default": 10},
            },
        },
    },
}


async def send_email(to: str, subject: str, body: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.n8n_webhook_base_url}/webhook/gmail-send",
                json={"to": to, "subject": subject, "body": body},
            )
            resp.raise_for_status()
            return f"Email sent to {to} with subject '{subject}'"
    except Exception as e:
        return f"Failed to send email: {e}"


async def read_email(filter: str = "is:unread", limit: int = 10) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.n8n_webhook_base_url}/webhook/gmail-read",
                json={"filter": filter, "limit": limit},
            )
            resp.raise_for_status()
            emails = resp.json()
            if not emails:
                return "No emails found matching the filter."
            lines = []
            for e in emails[:limit]:
                lines.append(f"From: {e.get('from','?')} | Subject: {e.get('subject','?')} | Date: {e.get('date','?')}\n{e.get('snippet','')}\n")
            return "\n---\n".join(lines)
    except Exception as e:
        return f"Failed to read email: {e}"
