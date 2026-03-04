# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Union

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Create an MCP server
mcp = FastMCP("Unsplash MCP Server")


@dataclass
class UnsplashPhoto:
    id: str
    description: Optional[str]
    urls: Dict[str, str]
    width: int
    height: int


VALID_SIZES = {"raw", "full", "regular", "small", "thumb"}


def _get_unsplash_headers() -> dict[str, str]:
    """Return Unsplash API headers, raising if the key is missing."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        raise ValueError("Missing UNSPLASH_ACCESS_KEY environment variable")
    return {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {access_key}",
    }


@mcp.tool()
async def search_photos(
        query: str,
        page: Union[int, str] = 1,
        per_page: Union[int, str] = 10,
        order_by: str = "relevant",
        color: Optional[str] = None,
        orientation: Optional[str] = None
) -> List[UnsplashPhoto]:
    """
    Search for Unsplash photos
    
    Args:
        query: Search keyword
        page: Page number (1-based)
        per_page: Results per page (1-30)
        order_by: Sort method (relevant or latest)
        color: Color filter (black_and_white, black, white, yellow, orange, red, purple, magenta, green, teal, blue)
        orientation: Orientation filter (landscape, portrait, squarish)
    
    Returns:
        List[UnsplashPhoto]: List of search results containing photo objects with the following properties:
            - id: Unique identifier for the photo
            - description: Optional text description of the photo
            - urls: Dictionary of available image URLs in different sizes
            - width: Original image width in pixels
            - height: Original image height in pixels
    """
    headers = _get_unsplash_headers()

    # 确保page是整数类型
    try:
        page_int = int(page)
    except (ValueError, TypeError):
        page_int = 1

    # 确保per_page是整数类型
    try:
        per_page_int = int(per_page)
    except (ValueError, TypeError):
        per_page_int = 10

    params = {
        "query": query,
        "page": page_int,
        "per_page": min(per_page_int, 30),
        "order_by": order_by,
    }

    if color:
        params["color"] = color
    if orientation:
        params["orientation"] = orientation

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.unsplash.com/search/photos",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            return [
                UnsplashPhoto(
                    id=photo["id"],
                    description=photo.get("description"),
                    urls=photo["urls"],
                    width=photo["width"],
                    height=photo["height"]
                )
                for photo in data["results"]
            ]
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Request error: {str(e)}")
        raise


@mcp.tool()
async def download_photo(
    photo_id: str,
    save_path: str,
    size: str = "regular",
) -> str:
    """
    Download an Unsplash photo by ID and save it to a local file.

    Args:
        photo_id: The Unsplash photo ID (from search results)
        save_path: Absolute file path where the image will be saved
        size: Image size variant (raw, full, regular, small, thumb)

    Returns:
        str: Confirmation message with photo ID, size, path, and byte count
    """
    if size not in VALID_SIZES:
        raise ValueError(
            f"Invalid size '{size}'. Must be one of: {', '.join(sorted(VALID_SIZES))}"
        )

    path = Path(save_path)
    if not path.is_absolute():
        raise ValueError(f"save_path must be absolute, got: {save_path}")
    if not path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {path.parent}")

    headers = _get_unsplash_headers()

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # Fetch photo metadata
            meta_resp = await client.get(
                f"https://api.unsplash.com/photos/{photo_id}",
                headers=headers,
            )
            if meta_resp.status_code == 404:
                raise ValueError(f"Photo not found: {photo_id}")
            meta_resp.raise_for_status()
            photo_data = meta_resp.json()

            # Trigger download tracking (required by Unsplash API guidelines)
            download_location = photo_data.get("links", {}).get("download_location")
            if download_location:
                try:
                    await client.get(download_location, headers=headers)
                except Exception:
                    pass  # tracking failure should not block the download

            # Download image bytes from CDN (no auth needed)
            image_url = photo_data["urls"][size]
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()

            # Write to disk
            path.write_bytes(img_resp.content)

            byte_count = len(img_resp.content)
            return (
                f"Downloaded photo {photo_id} ({size}) to {save_path} "
                f"({byte_count:,} bytes)"
            )
    except ValueError:
        raise
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"HTTP error fetching photo {photo_id}: "
            f"{e.response.status_code} - {e.response.text}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to download photo {photo_id}: {e}"
        ) from e


def main():
    """Entry point for uvx remote execution."""
    import sys
    import io

    # Ensure UTF-8 encoding for stdout/stderr
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    mcp.run()


if __name__ == "__main__":
    main()
