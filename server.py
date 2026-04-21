# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Union

import httpx
import piexif
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

# Load environment variables
load_dotenv()

UTM_PARAMS = "utm_source=unsplash_mcp&utm_medium=referral"
VALID_IMAGE_SIZES = {"raw", "full", "regular", "small", "thumb"}

# Regex to extract photo ID from filenames with the _unsplash-{id} convention
_UNSPLASH_ID_PATTERN = re.compile(r"_unsplash-([A-Za-z0-9_-]+)$")


def _embed_photo_id_in_path(save_path: Path, photo_id: str) -> Path:
    """Insert the photo ID into the filename: stem_unsplash-{id}.ext"""
    return save_path.with_name(
        f"{save_path.stem}_unsplash-{photo_id}{save_path.suffix}"
    )


def _extract_photo_id_from_path(file_path: Path) -> Optional[str]:
    """Extract photo ID from a filename containing _unsplash-{id} before the extension."""
    match = _UNSPLASH_ID_PATTERN.search(file_path.stem)
    if match:
        return match.group(1)
    return None


_EXIF_COMMENT_PREFIX = "unsplash:photo_id="


_EXIF_ASCII_PREFIX = b"ASCII\x00\x00\x00"


def _inject_exif_photo_id(image_bytes: bytes, photo_id: str) -> bytes:
    """Inject photo ID into EXIF UserComment of JPEG bytes. Non-JPEG bytes pass through unchanged."""
    import io

    if len(image_bytes) < 2 or image_bytes[0:2] != b"\xff\xd8":
        return image_bytes
    comment = f"{_EXIF_COMMENT_PREFIX}{photo_id}"
    user_comment_bytes = _EXIF_ASCII_PREFIX + comment.encode("ascii")
    try:
        try:
            exif_dict = piexif.load(image_bytes)
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment_bytes
        exif_bytes = piexif.dump(exif_dict)
        output = io.BytesIO()
        piexif.insert(exif_bytes, image_bytes, output)
        return output.getvalue()
    except Exception:
        return image_bytes


def _extract_exif_photo_id(image_bytes: bytes) -> Optional[str]:
    """Extract photo ID from EXIF UserComment. Returns None if not present or not JPEG."""
    if len(image_bytes) < 2 or image_bytes[0:2] != b"\xff\xd8":
        return None
    try:
        exif_dict = piexif.load(image_bytes)
        raw_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if not raw_comment:
            return None
        # Strip the 8-byte charset prefix (e.g. "ASCII\x00\x00\x00")
        if len(raw_comment) > 8:
            comment = raw_comment[8:].decode("ascii", errors="replace")
        else:
            return None
        if comment.startswith(_EXIF_COMMENT_PREFIX):
            return comment[len(_EXIF_COMMENT_PREFIX) :]
    except Exception:
        pass
    return None


# Create an MCP server
mcp = FastMCP("Unsplash MCP Server")


@dataclass
class UnsplashPhoto:
    id: str
    description: Optional[str]
    urls: Dict[str, str]
    width: int
    height: int


def _get_unsplash_headers() -> dict[str, str]:
    """Return Unsplash API headers, raising if the key is missing."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        raise ToolError("Missing UNSPLASH_ACCESS_KEY environment variable")
    return {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {access_key}",
    }


@dataclass
class PhotoAttribution:
    photo_id: str
    description: Optional[str]
    alt_description: Optional[str]
    photo_url: str
    image_url: str
    photographer_name: str
    photographer_url: str
    urls: Dict[str, str]
    attribution_markdown: str


@mcp.tool()
async def search_photos(
    query: str,
    page: Union[int, str] = 1,
    per_page: Union[int, str] = 10,
    order_by: str = "relevant",
    color: Optional[str] = None,
    orientation: Optional[str] = None,
    ctx: Optional[Context] = None,
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
                "https://api.unsplash.com/search/photos", params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            return [
                UnsplashPhoto(
                    id=photo["id"],
                    description=photo.get("description"),
                    urls=photo["urls"],
                    width=photo["width"],
                    height=photo["height"],
                )
                for photo in data["results"]
            ]
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code} - {e.response.text}"
        if ctx:
            await ctx.error(error_msg)
        raise ToolError(f"HTTP error searching photos: {error_msg}") from e
    except Exception as e:
        error_msg = f"Request error: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise ToolError(f"Failed to search photos: {e}") from e


@mcp.tool()
async def download_photo(
    photo_id: str,
    save_path: str,
    size: str = "regular",
    create_directories: bool = False,
    embed_photo_id: bool = True,
) -> str:
    """
    Download an Unsplash photo by ID and save it to a local file.

    Args:
        photo_id: The Unsplash photo ID (from search results)
        save_path: Absolute file path where the image will be saved
        size: Image size variant (raw, full, regular, small, thumb)
        create_directories: If True, create parent directories if they don't exist
        embed_photo_id: If True (default), the photo ID is embedded in the filename
                        (e.g., mountain.jpg becomes mountain_unsplash-abc123.jpg).
                        This allows recovering the photo ID from the file later.

    Returns:
        str: Confirmation message with photo ID, size, path, and byte count
    """
    if size not in VALID_IMAGE_SIZES:
        raise ToolError(
            f"Invalid size '{size}'. Must be one of: {', '.join(sorted(VALID_IMAGE_SIZES))}"
        )

    path = Path(save_path)
    if not path.is_absolute():
        raise ToolError(f"save_path must be absolute, got: {save_path}")

    if embed_photo_id:
        path = _embed_photo_id_in_path(path, photo_id)

    # Handle parent directory
    if not path.parent.exists():
        if create_directories:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise ToolError(
                f"Parent directory does not exist: {path.parent}. "
                f"Set create_directories=True to create it automatically."
            )

    # Prevent file overwrite
    if path.exists():
        raise ToolError(
            f"File already exists at {path}. "
            f"Please choose a different path or delete the existing file first."
        )

    headers = _get_unsplash_headers()

    try:
        # Increase timeout for large files (especially raw images)
        timeout = 120.0 if size in ("raw", "full") else 60.0
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            # Fetch photo metadata
            meta_resp = await client.get(
                f"https://api.unsplash.com/photos/{photo_id}",
                headers=headers,
            )
            if meta_resp.status_code == 404:
                raise ToolError(f"Photo not found: {photo_id}")
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

            # Inject photo ID into EXIF metadata (JPEG only, no quality loss)
            image_data = _inject_exif_photo_id(img_resp.content, photo_id)

            # Write to disk atomically: fail if file already exists
            try:
                with path.open("xb") as f:
                    f.write(image_data)
            except FileExistsError as e:
                raise ToolError(
                    f"File already exists at {path}. "
                    f"Please choose a different path or delete the existing file first."
                ) from e

            byte_count = len(image_data)
            return (
                f"Downloaded photo {photo_id} ({size}) to {path} ({byte_count:,} bytes)"
            )
    except ToolError:
        raise
    except httpx.HTTPStatusError as e:
        raise ToolError(
            f"HTTP error fetching photo {photo_id}: "
            f"{e.response.status_code} - {e.response.text}"
        ) from e
    except Exception as e:
        raise ToolError(f"Failed to download photo {photo_id}: {e}") from e


@mcp.tool()
async def get_photo_attribution(
    photo_id: str,
    image_size: str = "regular",
    ctx: Optional[Context] = None,
) -> PhotoAttribution:
    """
    Get attribution information for an Unsplash photo.

    Returns properly formatted attribution text compliant with Unsplash API
    guidelines, in both structured JSON and ready-to-use Markdown.

    Args:
        photo_id: The unique identifier of the Unsplash photo (e.g., "abc123")
        image_size: Size of image URL to use in attribution (raw, full, regular, small, thumb).
                    Defaults to "regular" (1080px wide).

    Returns:
        PhotoAttribution: Attribution data containing:
            - photo_id: Unique identifier for the photo
            - description: Optional photo description from photographer
            - alt_description: Optional AI-generated alt text
            - photo_url: Link to photo page on Unsplash (with UTM params)
            - image_url: Direct image URL for the selected size
            - photographer_name: Name of the photographer
            - photographer_url: Link to photographer's Unsplash profile (with UTM params)
            - urls: Dictionary of all available image URLs by size
            - attribution_markdown: Ready-to-use Markdown attribution text
    """
    headers = _get_unsplash_headers()

    if image_size not in VALID_IMAGE_SIZES:
        raise ToolError(
            f"Invalid image_size '{image_size}'. "
            f"Must be one of: {', '.join(sorted(VALID_IMAGE_SIZES))}"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.unsplash.com/photos/{photo_id}", headers=headers
            )
            response.raise_for_status()
            data = response.json()

            description = data.get("description")
            alt_description = data.get("alt_description")
            urls = data.get("urls", {})
            photographer_name = data["user"]["name"]

            raw_photo_url = data["links"]["html"]
            raw_profile_url = data["user"]["links"]["html"]

            separator = "&" if "?" in raw_photo_url else "?"
            photo_url = f"{raw_photo_url}{separator}{UTM_PARAMS}"

            separator = "&" if "?" in raw_profile_url else "?"
            photographer_url = f"{raw_profile_url}{separator}{UTM_PARAMS}"

            unsplash_url = f"https://unsplash.com?{UTM_PARAMS}"

            image_url = urls.get(image_size, urls.get("regular", ""))

            alt_text = alt_description or description or "Unsplash photo"

            attribution_markdown = (
                f"![{alt_text}]({image_url})\n"
                f"*Photo by [{photographer_name}]({photographer_url}) "
                f"on [Unsplash]({unsplash_url})*"
            )

            return PhotoAttribution(
                photo_id=data["id"],
                description=description,
                alt_description=alt_description,
                photo_url=photo_url,
                image_url=image_url,
                photographer_name=photographer_name,
                photographer_url=photographer_url,
                urls=urls,
                attribution_markdown=attribution_markdown,
            )
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code} - {e.response.text}"
        if ctx:
            await ctx.error(error_msg)
        raise ToolError(
            f"HTTP error fetching attribution for {photo_id}: {error_msg}"
        ) from e
    except Exception as e:
        error_msg = f"Request error: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise ToolError(f"Failed to fetch attribution for {photo_id}: {e}") from e


@mcp.tool()
async def get_photo_id_from_filename(
    file_path: str,
) -> str:
    """
    Extract the Unsplash photo ID from a filename that was saved with embed_photo_id=True.

    Looks for the _unsplash-{id} pattern in the filename. For example,
    'mountain_unsplash-abc123.jpg' yields photo ID 'abc123'.

    Args:
        file_path: Path to the downloaded image file

    Returns:
        str: The extracted Unsplash photo ID
    """
    p = Path(file_path)
    if not p.is_file():
        raise ToolError(f"File does not exist or is not a file: {file_path}")

    photo_id = _extract_photo_id_from_path(p)
    if photo_id is None:
        raise ToolError(
            f"No Unsplash photo ID found in filename '{p.name}'. "
            f"The file may not have been downloaded with embed_photo_id=True."
        )
    return photo_id


@mcp.tool()
async def get_photo_id_from_exif(
    file_path: str,
) -> str:
    """
    Extract the Unsplash photo ID from a file's EXIF metadata.

    Reads the EXIF UserComment field for a photo ID stored during download.
    Only works with JPEG files that were downloaded with this server.

    Args:
        file_path: Path to the downloaded image file

    Returns:
        str: The extracted Unsplash photo ID
    """
    p = Path(file_path)
    if not p.is_file():
        raise ToolError(f"File does not exist or is not a file: {file_path}")

    image_bytes = p.read_bytes()
    photo_id = _extract_exif_photo_id(image_bytes)
    if photo_id is None:
        raise ToolError(
            f"No Unsplash photo ID found in EXIF metadata for '{p.name}'. "
            f"The file may not be a JPEG or may not have been downloaded with this server."
        )
    return photo_id


def main():
    """Entry point for uvx remote execution."""
    import sys
    import io

    # Ensure UTF-8 encoding for stdout/stderr
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    mcp.run()


if __name__ == "__main__":
    main()
