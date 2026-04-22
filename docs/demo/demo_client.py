"""Fixture-backed demo driver for the Unsplash MCP server.

Run with `UNSPLASH_MCP_DEMO_MODE=1` to patch httpx and serve canned fixtures
from ``docs/demo/fixtures/`` instead of hitting the real Unsplash API.
This is what the VHS tape executes to produce ``docs/demo.gif``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


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
    """Monkey-patch httpx.AsyncClient.get to dispatch on URL."""
    import httpx

    search_body = json.loads((FIXTURES / "search_mountain.json").read_text())
    photo_body = json.loads((FIXTURES / "photo_meta.json").read_text())
    image_bytes = (FIXTURES / "image_regular.bin").read_bytes()

    async def fake_get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        await asyncio.sleep(0)  # preserve async semantics
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


# -- patch must run before importing server so FastMCP clients pick up the stub
if os.getenv("UNSPLASH_MCP_DEMO_MODE") == "1":
    _install_fixture_patch()

from server import (  # noqa: E402
    download_photo,
    get_photo_attribution,
    get_photo_id_from_filename,
    search_photos,
)


# Colours for prompt-like output; skipped when stdout isn't a TTY.
def _c(code: str) -> str:
    return f"\033[{code}m" if sys.stdout.isatty() else ""


CYAN = _c("36")
GREEN = _c("32")
DIM = _c("2")
BOLD = _c("1")
RESET = _c("0")


def _banner(text: str) -> None:
    print(f"{BOLD}{CYAN}{text}{RESET}")


def _call(signature: str) -> None:
    print(f"{GREEN}>>>{RESET} {signature}")


def _result(label: str, value: str) -> None:
    print(f"{DIM}   {label}:{RESET} {value}")


async def main() -> None:
    _banner("# Unsplash MCP Server — demo")
    time.sleep(0.6)

    _call('search_photos(query="mountain", per_page=3)')
    photos = await search_photos(query="mountain", per_page=3)
    for i, photo in enumerate(photos, 1):
        _result(f"{i}", f"{photo.id}  ·  {photo.alt_description}")
    time.sleep(1.2)

    first_id = photos[0].id
    _call(f'get_photo_attribution(photo_id="{first_id}")')
    attribution = await get_photo_attribution(photo_id=first_id)
    _result("markdown", attribution.attribution_markdown)
    time.sleep(1.5)

    save_path = "/tmp/demo/mountain.jpg"
    _call(f'download_photo(photo_id="{first_id}", save_path="{save_path}")')
    download = await download_photo(
        photo_id=first_id,
        save_path=save_path,
        create_directories=True,
    )
    _result("saved", f"{download.byte_count} bytes → {download.path}")
    time.sleep(1.2)

    _call(f'get_photo_id_from_filename("{download.path}")')
    extracted = await get_photo_id_from_filename(download.path)
    _result("photo_id", extracted)
    time.sleep(1.0)

    print()
    _banner("# Regenerate this GIF with:  make demo")


if __name__ == "__main__":
    asyncio.run(main())
