from .browser import browse_web, TOOL_DEFINITION as BROWSE_TOOL
from .home_assistant import control_home, TOOL_DEFINITION as HA_TOOL
from .nextcloud import manage_files, TOOL_DEFINITION as NEXTCLOUD_TOOL
from .plex import plex_control, TOOL_DEFINITION as PLEX_TOOL
from .proxmox import proxmox_action, TOOL_DEFINITION as PROXMOX_TOOL
from .gmail import send_email, read_email, SEND_TOOL_DEFINITION, READ_TOOL_DEFINITION
from .memory_tool import save_memory, query_memory, SAVE_MEMORY_DEFINITION, QUERY_MEMORY_DEFINITION
from .truenas import truenas_action, TOOL_DEFINITION as TRUENAS_TOOL
from .ssh_tool import ssh_exec, ssh_docker_action, EXEC_TOOL_DEFINITION as SSH_EXEC_TOOL, DOCKER_TOOL_DEFINITION as SSH_DOCKER_TOOL
from .security import security_monitor, TOOL_DEFINITION as SECURITY_TOOL
from .youtube import (
    youtube_research, youtube_write_script, youtube_create_video,
    youtube_upload, youtube_generate_thumbnail,
    RESEARCH_TOOL_DEFINITION, SCRIPT_TOOL_DEFINITION, VIDEO_TOOL_DEFINITION,
    UPLOAD_TOOL_DEFINITION, THUMBNAIL_TOOL_DEFINITION,
)

ALL_TOOL_DEFINITIONS = [
    BROWSE_TOOL,
    HA_TOOL,
    NEXTCLOUD_TOOL,
    PLEX_TOOL,
    PROXMOX_TOOL,
    SEND_TOOL_DEFINITION,
    READ_TOOL_DEFINITION,
    SAVE_MEMORY_DEFINITION,
    QUERY_MEMORY_DEFINITION,
    TRUENAS_TOOL,
    SSH_EXEC_TOOL,
    SSH_DOCKER_TOOL,
    SECURITY_TOOL,
    RESEARCH_TOOL_DEFINITION,
    SCRIPT_TOOL_DEFINITION,
    VIDEO_TOOL_DEFINITION,
    UPLOAD_TOOL_DEFINITION,
    THUMBNAIL_TOOL_DEFINITION,
]

__all__ = [
    "browse_web", "control_home", "manage_files", "plex_control",
    "proxmox_action", "send_email", "read_email",
    "save_memory", "query_memory",
    "truenas_action", "ssh_exec", "ssh_docker_action", "security_monitor",
    "youtube_research", "youtube_write_script", "youtube_create_video",
    "youtube_upload", "youtube_generate_thumbnail",
    "ALL_TOOL_DEFINITIONS",
]
