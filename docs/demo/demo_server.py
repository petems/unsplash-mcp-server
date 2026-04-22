"""Stdio MCP entrypoint for the demo.

Patches ``httpx.AsyncClient.get`` with fixture responses when
``UNSPLASH_MCP_DEMO_MODE=1``, then runs the real MCP server over stdio.
The demo client spawns this script as an MCP subprocess so the GIF shows
genuine JSON-RPC tool calls rather than in-process Python function calls.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the repo root (which holds server.py) is on sys.path when this script
# is spawned as a subprocess — Python's default sys.path[0] is the script's
# directory (docs/demo/), not the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIXTURES = Path(__file__).parent / "fixtures"


class _FakeResponse:
    def __init__(
        self, *, status_code: int = 200, json_body: Any = None, content: bytes = b""
    ):
        self.status_code = status_code
        self._json = json_body
        self.content = content
        self.text = "" if json_body is None else json.dumps(json_body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(
                f"Fixture returned {self.status_code}",
                request=None,  # type: ignore[arg-type]
                response=self,  # type: ignore[arg-type]
            )

    def json(self) -> Any:
        return self._json


def _install_fixture_patch() -> None:
    import httpx

    search_body = json.loads((_FIXTURES / "search_mountain.json").read_text())
    photo_body = json.loads((_FIXTURES / "photo_meta.json").read_text())
    image_bytes = (_FIXTURES / "image_regular.bin").read_bytes()

    async def fake_get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        await asyncio.sleep(0)
        if "api.unsplash.com/search/photos" in url:
            return _FakeResponse(json_body=search_body)
        if "api.unsplash.com/photos/" in url and "/download" in url:
            return _FakeResponse(json_body={"url": photo_body["urls"]["regular"]})
        if "api.unsplash.com/photos/" in url:
            return _FakeResponse(json_body=photo_body)
        if "images.unsplash.com" in url:
            return _FakeResponse(content=image_bytes)
        return _FakeResponse(
            status_code=404, json_body={"error": f"no fixture for {url}"}
        )

    httpx.AsyncClient.get = fake_get  # type: ignore[method-assign]


if os.getenv("UNSPLASH_MCP_DEMO_MODE") == "1":
    _install_fixture_patch()

from server import mcp  # noqa: E402


if __name__ == "__main__":
    mcp.run()
