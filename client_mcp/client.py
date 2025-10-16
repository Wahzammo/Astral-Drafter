import asyncio
import sys
import json
import ollama
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from pathlib import Path
import os
import stat
import subprocess

from mcp import ClientSession, StdioServerParameters # Assuming mcp library is correct
from mcp.client.stdio import stdio_client

# New Imports for Robustness and Local Time
import socket
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------
# 🛡️ SECURITY & RELIABILITY FIXES
# ------------------------------------------------------------------

# 1. FIX: Removed external ipapi.co call (DoS/IP Leak)
DEFAULT_TIMEZONE = os.environ.get("MCP_DEFAULT_TIMEZONE", "Australia/Melbourne")
API_TIMEOUT = 5 # Timeout for any remaining external calls (5 seconds is reasonable)

def get_current_time() -> str:
    try:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        tz_abbrev = now.strftime('%Z')
        return (f"Current local time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {tz_abbrev}\n"
                f"ISO format: {now.isoformat()}")
    except Exception:
        now = datetime.now(ZoneInfo('UTC'))
        return (f"Could not use configured timezone. Current UTC time:\n"
                f"{now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} UTC\n"
                f"ISO format: {now.isoformat()}")

# 2. FIX: Critical RCE/Tool Execution Harden (Finding 3A)
# Define an explicit allowlist directory (scripts must live under this dir).
# Require absolute canonicalization of script path and verify it is inside the allowlist dir.
SCRIPT_ALLOWLIST_DIR = Path(os.environ.get("MCP_SCRIPT_ALLOWLIST_DIR", str(Path.home() / ".mcp_allowed_servers"))).resolve()

# Ensure directory exists and is owner-only
if not SCRIPT_ALLOWLIST_DIR.exists():
    SCRIPT_ALLOWLIST_DIR.mkdir(parents=True, exist_ok=True)
    try:
        SCRIPT_ALLOWLIST_DIR.chmod(0o700)
    except Exception:
        # Best-effort; some filesystems/OS won't support chmod the same way
        pass

TOOL_ALLOWLIST: List[str] = [
    "get_current_time",
    # Add other safe, read-only tools here.
]

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama_model = os.environ.get("MCP_DEFAULT_OLLAMA_MODEL", "llama3:8b-instruct")

    def _validate_and_resolve_script(self, server_script_path: str) -> Path:
        """
        Validate the provided script path:
        - Must be under SCRIPT_ALLOWLIST_DIR
        - Must be a regular file
        - Must have a safe extension (.py or .js)
        """
        p = Path(server_script_path).expanduser()
        try:
            resolved = p.resolve(strict=True)
        except FileNotFoundError:
            # Do not allow non-existent scripts to be executed
            raise ValueError("Server script does not exist or is not accessible")

        try:
            allowed_dir = SCRIPT_ALLOWLIST_DIR
            allowed_dir = allowed_dir.resolve(strict=True)
        except FileNotFoundError:
            raise RuntimeError("Configured script allowlist directory is missing")

        if not str(resolved).startswith(str(allowed_dir) + os.sep):
            raise ValueError("Server script is not inside the allowed scripts directory")

        if not resolved.is_file():
            raise ValueError("Server script path is not a file")

        if not (resolved.suffix == ".py" or resolved.suffix == ".js"):
            raise ValueError("Server script must be a .py or .js file")

        # Optional: check file mode to ensure not world-writable
        try:
            st = resolved.stat()
            if bool(st.st_mode & (stat.S_IWOTH | stat.S_IWGRP)):
                raise ValueError("Server script has insecure permissions (group/other writable)")
        except Exception:
            pass

        return resolved

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server after validating the script location"""
        resolved_script = self._validate_and_resolve_script(server_script_path)
        is_python = resolved_script.suffix == '.py'
        is_js = resolved_script.suffix == '.js'

        command = "python" if is_python else "node"
        # Use absolute path to script; do NOT use shell=True and do not pass unvalidated environment
        server_params = StdioServerParameters(
            command=command,
            args=[str(resolved_script)],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

    # ... rest of client implementation ...
