import json
import structlog
from typing import Optional
from providers import get_provider, Message, LLMResponse, ToolCall
from memory import MemoryManager
from tools import (
    ALL_TOOL_DEFINITIONS,
    browse_web, control_home, manage_files, plex_control,
    proxmox_action, send_email, read_email,
    save_memory, query_memory,
    truenas_action, ssh_exec, ssh_docker_action, security_monitor,
    youtube_research, youtube_write_script, youtube_create_video,
    youtube_upload, youtube_generate_thumbnail,
)

log = structlog.get_logger()

SYSTEM_PROMPT = """You are a personal AI assistant running on a private home server. You are the user's IT department, personal assistant, homelab manager, and digital life helper.

You have access to the following tools:

BROWSING & WEB:
- browse_web: Browse any URL and read web content

SMART HOME:
- control_home: Control Home Assistant smart home devices and automations

STORAGE & FILES:
- manage_files: Manage files on Nextcloud (upload, download, list, delete)

MEDIA:
- plex_control: Control Plex media server (search, play, manage libraries)

HOMELAB & INFRASTRUCTURE:
- proxmox_action: Manage Proxmox VMs and containers (start, stop, snapshots, resource usage)
- truenas_action: Manage TrueNAS storage server (pools, datasets, alerts, services, scrub)
- ssh_exec: Execute shell commands on any registered Linux server or TrueNAS via SSH
- ssh_docker_action: Manage Docker containers on remote servers (list, update, restart, logs, pull images)
- security_monitor: Monitor security on remote servers (failed logins, open ports, auth logs, firewall, updates)

COMMUNICATION:
- send_email / read_email: Send and read Gmail via n8n

MEMORY:
- save_memory: Save important facts to long-term persistent memory
- query_memory: Search long-term memory for relevant context

YOUTUBE & CONTENT CREATION:
- youtube_research: Research trending topics, search videos, keyword research for a given niche
- youtube_write_script: Write a full YouTube video script with hook, sections, and call-to-action
- youtube_create_video: Create a slideshow/narration MP4 video with TTS audio and AI-generated images
- youtube_upload: Upload a video to YouTube with title, description, tags, and thumbnail
- youtube_generate_thumbnail: Generate a YouTube thumbnail using Stability AI or DALL-E

Guidelines:
- Always check memory for relevant context before answering
- Save important facts the user shares about themselves or their preferences
- For homelab tasks, use ssh_exec for one-off commands, ssh_docker_action for Docker management
- Proactively suggest security checks or updates when relevant
- For YouTube: research first → write script → create video → generate thumbnail → upload
- Be concise but thorough
- When unsure, ask a clarifying question rather than guessing
- You are running on the user's private server — you can access local services freely
- Never expose SSH credentials or API keys in responses
"""


class Agent:
    def __init__(self, memory_manager: MemoryManager, db_pool=None, integration_configs: dict = None):
        self.memory = memory_manager
        self.db_pool = db_pool
        self.integrations = integration_configs or {}

    async def run(
        self,
        user_message: str,
        session_id: str,
        provider_name: Optional[str] = None,
    ) -> str:
        provider = get_provider(provider_name)

        relevant_memories = await self.memory.search_memories(user_message, limit=5)
        memory_context = ""
        if relevant_memories:
            memory_context = "\n\nRelevant memories:\n" + "\n".join(
                f"- [{m['category']}] {m['content']}" for m in relevant_memories
            )

        history = await self.memory.get_conversation(session_id, limit=20)

        messages: list[Message] = [
            Message(role="system", content=SYSTEM_PROMPT + memory_context)
        ]
        for h in history:
            msg = Message(role=h["role"], content=h["content"] or "")
            if h.get("tool_calls"):
                msg.tool_calls = json.loads(h["tool_calls"]) if isinstance(h["tool_calls"], str) else h["tool_calls"]
            if h.get("tool_call_id"):
                msg.tool_call_id = h["tool_call_id"]
            messages.append(msg)

        messages.append(Message(role="user", content=user_message))
        await self.memory.save_conversation(session_id, "user", user_message)

        max_iterations = 10
        for iteration in range(max_iterations):
            response: LLMResponse = await provider.chat(
                messages=messages,
                tools=ALL_TOOL_DEFINITIONS,
                temperature=0.7,
            )

            if not response.tool_calls:
                final_content = response.content or ""
                await self.memory.save_conversation(session_id, "assistant", final_content)
                return final_content

            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in response.tool_calls
                ],
            )
            messages.append(assistant_msg)
            await self.memory.save_conversation(
                session_id, "assistant", response.content or "",
                tool_calls=assistant_msg.tool_calls,
            )

            for tc in response.tool_calls:
                tool_result = await self._dispatch_tool(tc)
                log.info("tool_called", tool=tc.name, result_preview=str(tool_result)[:100])

                tool_msg = Message(
                    role="tool",
                    content=str(tool_result),
                    tool_call_id=tc.id,
                    name=tc.name,
                )
                messages.append(tool_msg)
                await self.memory.save_conversation(
                    session_id, "tool", str(tool_result), tool_call_id=tc.id
                )

        return "I reached the maximum number of steps. Please try rephrasing your request."

    async def _get_integration_config(self, name: str) -> dict:
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT config FROM integrations WHERE name = $1 AND enabled = true", name
                    )
                    if row:
                        cfg = row["config"]
                        return json.loads(cfg) if isinstance(cfg, str) else (cfg or {})
            except Exception:
                pass
        return self.integrations.get(name, {})

    async def _dispatch_tool(self, tc: ToolCall) -> str:
        args = tc.arguments
        try:
            if tc.name == "browse_web":
                return await browse_web(**args)
            elif tc.name == "control_home":
                config = await self._get_integration_config("home_assistant")
                return await control_home(config=config, **args)
            elif tc.name == "manage_files":
                config = await self._get_integration_config("nextcloud")
                return await manage_files(config=config, **args)
            elif tc.name == "plex_control":
                config = await self._get_integration_config("plex")
                return await plex_control(config=config, **args)
            elif tc.name == "proxmox_action":
                config = await self._get_integration_config("proxmox")
                return await proxmox_action(config=config, **args)
            elif tc.name == "send_email":
                config = await self._get_integration_config("gmail")
                return await send_email(config=config, **args)
            elif tc.name == "read_email":
                config = await self._get_integration_config("gmail")
                return await read_email(config=config, **args)
            elif tc.name == "save_memory":
                return await save_memory(self.memory, **args)
            elif tc.name == "query_memory":
                return await query_memory(self.memory, **args)
            elif tc.name == "truenas_action":
                config = await self._get_integration_config("truenas")
                return await truenas_action(config=config, **args)
            elif tc.name == "ssh_exec":
                return await ssh_exec(self.db_pool, **args)
            elif tc.name == "ssh_docker_action":
                return await ssh_docker_action(self.db_pool, **args)
            elif tc.name == "security_monitor":
                return await security_monitor(self.db_pool, **args)
            elif tc.name == "youtube_research":
                config = await self._get_integration_config("youtube")
                return await youtube_research(config=config, **args)
            elif tc.name == "youtube_write_script":
                provider = get_provider()
                return await youtube_write_script(llm_provider=provider, **args)
            elif tc.name == "youtube_create_video":
                config = await self._get_integration_config("youtube")
                stab_cfg = await self._get_integration_config("stability")
                merged = {**config, **stab_cfg}
                return await youtube_create_video(config=merged, **args)
            elif tc.name == "youtube_upload":
                config = await self._get_integration_config("youtube")
                return await youtube_upload(config=config, **args)
            elif tc.name == "youtube_generate_thumbnail":
                yt_cfg = await self._get_integration_config("youtube")
                stab_cfg = await self._get_integration_config("stability")
                merged = {**yt_cfg, **stab_cfg}
                return await youtube_generate_thumbnail(config=merged, **args)
            else:
                return f"Unknown tool: {tc.name}"
        except Exception as e:
            log.error("tool_error", tool=tc.name, error=str(e))
            return f"Tool error ({tc.name}): {e}"
