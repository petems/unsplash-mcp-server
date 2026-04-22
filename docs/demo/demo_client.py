"""MCP client that drives ``docs/demo/demo_server.py`` over stdio.

This is a real MCP client — it spawns the server as a subprocess and
exchanges JSON-RPC messages over stdio, exactly like Claude Code or
MCP Inspector would. The server subprocess handles fixture backing
internally, so the client stays simple and stateless.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

_SERVER = Path(__file__).parent / "demo_server.py"


def _c(code: str) -> str:
    return f"\033[{code}m" if sys.stdout.isatty() else ""


CYAN, GREEN, DIM, BOLD, RESET = _c("36"), _c("32"), _c("2"), _c("1"), _c("0")


def _banner(text: str) -> None:
    print(f"{BOLD}{CYAN}{text}{RESET}")


def _call(signature: str) -> None:
    print(f"{GREEN}>>>{RESET} {signature}")


def _result(label: str, value: str) -> None:
    print(f"{DIM}   {label}:{RESET} {value}")


def _field(obj: Any, name: str) -> Any:
    """Attr/dict lookup — CallToolResult.data may hydrate as either shape."""
    value = getattr(obj, name, None)
    if value is not None:
        return value
    if isinstance(obj, dict):
        return obj.get(name)
    return None


def _build_transport() -> StdioTransport:
    # Use the same interpreter that runs this script so fastmcp is in scope.
    # Inherit os.environ so $PATH and the uv venv survive into the subprocess;
    # default demo mode + placeholder key unless the caller overrides.
    env = os.environ.copy()
    env.setdefault("UNSPLASH_MCP_DEMO_MODE", "1")
    env.setdefault("UNSPLASH_ACCESS_KEY", "demo-mode-no-real-key")
    # Quiet the spawned server: banner + info logs would otherwise dominate
    # the GIF. Stderr messages from the server are still captured by the
    # transport, just not displayed.
    env.setdefault("FASTMCP_SHOW_SERVER_BANNER", "false")
    env.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
    return StdioTransport(command=sys.executable, args=[str(_SERVER)], env=env)


async def main() -> None:
    _banner("# Unsplash MCP Server — stdio demo")
    time.sleep(0.5)
    print(f"{DIM}   spawning server subprocess over MCP stdio …{RESET}")
    time.sleep(0.4)

    async with Client(_build_transport()) as client:
        tools = await client.list_tools()
        _result("tools", ", ".join(t.name for t in tools))
        time.sleep(1.2)

        _call('call_tool("search_photos", {"query": "mountain", "per_page": 3})')
        result = await client.call_tool(
            "search_photos", {"query": "mountain", "per_page": 3}
        )
        photos = result.data or []
        for i, photo in enumerate(photos, 1):
            _result(
                f"{i}",
                f"{_field(photo, 'id')}  ·  {_field(photo, 'alt_description')}",
            )
        time.sleep(1.4)

        first_id = _field(photos[0], "id")
        _call(f'call_tool("get_photo_attribution", {{"photo_id": "{first_id}"}})')
        result = await client.call_tool("get_photo_attribution", {"photo_id": first_id})
        _result("markdown", str(_field(result.data, "attribution_markdown")))
        time.sleep(1.5)

        save_path = "/tmp/demo/mountain.jpg"
        _call(
            f'call_tool("download_photo", {{"photo_id": "{first_id}", '
            f'"save_path": "{save_path}"}})'
        )
        result = await client.call_tool(
            "download_photo",
            {
                "photo_id": first_id,
                "save_path": save_path,
                "create_directories": True,
            },
        )
        file_path = _field(result.data, "path")
        _result(
            "saved",
            f"{_field(result.data, 'byte_count')} bytes → {file_path}",
        )
        time.sleep(1.3)

        _call(
            f'call_tool("get_photo_id_from_filename", {{"file_path": "{file_path}"}})'
        )
        result = await client.call_tool(
            "get_photo_id_from_filename", {"file_path": file_path}
        )
        extracted = result.data if isinstance(result.data, str) else str(result.data)
        _result("photo_id", extracted)
        time.sleep(1.0)

    print()
    _banner("# Regenerate this GIF with:  make demo")


if __name__ == "__main__":
    asyncio.run(main())
