# -*- coding: utf-8 -*-
"""Tests for Unsplash MCP server photo ID embedding and extraction."""

from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError

from server import (
    _embed_photo_id_in_path,
    _extract_photo_id_from_path,
    _inject_exif_photo_id,
    _extract_exif_photo_id,
    _build_attribution_markdown,
    _with_utm_params,
    _validate_photo_id,
    VALID_ORDER_BY,
    VALID_COLORS,
    VALID_ORIENTATIONS,
)


class TestEmbedPhotoIdInPath:
    def test_basic(self):
        result = _embed_photo_id_in_path(Path("/tmp/mountain.jpg"), "abc123")
        assert result == Path("/tmp/mountain_unsplash-abc123.jpg")

    def test_no_extension(self):
        result = _embed_photo_id_in_path(Path("/tmp/photo"), "abc123")
        assert result == Path("/tmp/photo_unsplash-abc123")

    def test_multi_dot_filename(self):
        result = _embed_photo_id_in_path(Path("/tmp/photo.2024.jpg"), "abc123")
        assert result == Path("/tmp/photo.2024_unsplash-abc123.jpg")

    def test_complex_id_with_hyphens(self):
        result = _embed_photo_id_in_path(Path("/tmp/img.png"), "Dwu85P9-SOIk")
        assert result == Path("/tmp/img_unsplash-Dwu85P9-SOIk.png")

    def test_complex_id_with_underscore(self):
        result = _embed_photo_id_in_path(Path("/tmp/img.png"), "abc_123")
        assert result == Path("/tmp/img_unsplash-abc_123.png")


class TestExtractPhotoIdFromPath:
    def test_basic(self):
        result = _extract_photo_id_from_path(Path("/tmp/mountain_unsplash-abc123.jpg"))
        assert result == "abc123"

    def test_no_extension(self):
        result = _extract_photo_id_from_path(Path("/tmp/photo_unsplash-abc123"))
        assert result == "abc123"

    def test_complex_id(self):
        result = _extract_photo_id_from_path(Path("/tmp/img_unsplash-Dwu85P9SOIk.png"))
        assert result == "Dwu85P9SOIk"

    def test_id_with_hyphens(self):
        result = _extract_photo_id_from_path(Path("/tmp/file_unsplash-ab-cd.jpg"))
        assert result == "ab-cd"

    def test_id_with_underscore(self):
        result = _extract_photo_id_from_path(Path("/tmp/file_unsplash-abc_123.jpg"))
        assert result == "abc_123"

    def test_no_match(self):
        result = _extract_photo_id_from_path(Path("/tmp/mountain.jpg"))
        assert result is None

    def test_no_match_partial(self):
        result = _extract_photo_id_from_path(Path("/tmp/unsplash-abc123.jpg"))
        assert result is None


class TestRoundTrip:
    def test_embed_then_extract(self):
        original = Path("/tmp/mountain.jpg")
        photo_id = "Dwu85P9SOIk"
        embedded = _embed_photo_id_in_path(original, photo_id)
        extracted = _extract_photo_id_from_path(embedded)
        assert extracted == photo_id

    def test_round_trip_with_hyphens(self):
        original = Path("/tmp/photo.jpg")
        photo_id = "a-b-c-123"
        embedded = _embed_photo_id_in_path(original, photo_id)
        extracted = _extract_photo_id_from_path(embedded)
        assert extracted == photo_id


class TestGetPhotoIdFromFilename:
    @pytest.mark.anyio
    async def test_valid_file(self, tmp_path):
        from server import get_photo_id_from_filename

        temp_file = tmp_path / "test_unsplash-abc123.jpg"
        temp_file.touch()

        result = await get_photo_id_from_filename(str(temp_file))
        assert result == "abc123"

    @pytest.mark.anyio
    async def test_no_id_in_filename(self, tmp_path):
        from server import get_photo_id_from_filename

        temp_file = tmp_path / "plain_photo.jpg"
        temp_file.touch()

        with pytest.raises(ToolError, match="No Unsplash photo ID found"):
            await get_photo_id_from_filename(str(temp_file))

    @pytest.mark.anyio
    async def test_file_not_found(self):
        from server import get_photo_id_from_filename

        with pytest.raises(ToolError, match="File does not exist or is not a file"):
            await get_photo_id_from_filename("/tmp/nonexistent_file_12345.jpg")


# Minimal valid JPEG with enough structure for piexif to parse
def _minimal_jpeg() -> bytes:
    import struct

    soi = b"\xff\xd8"
    # APP0 marker with JFIF header
    app0_data = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    app0 = b"\xff\xe0" + struct.pack(">H", len(app0_data) + 2) + app0_data
    # Quantization table (DQT)
    dqt = b"\xff\xdb\x00\x43\x00" + bytes(64)
    # Start of frame (SOF0) - 1x1 pixel, 1 component
    sof = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    # Huffman table (DHT)
    dht = (
        b"\xff\xc4\x00\x1f\x00"
        b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    )
    # Start of scan (SOS)
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40"
    eoi = b"\xff\xd9"
    return soi + app0 + dqt + sof + dht + sos + eoi


class TestInjectExifPhotoId:
    def test_round_trip(self):
        jpeg = _minimal_jpeg()
        injected = _inject_exif_photo_id(jpeg, "abc123")
        assert injected != jpeg  # bytes were modified
        extracted = _extract_exif_photo_id(injected)
        assert extracted == "abc123"

    def test_complex_id(self):
        jpeg = _minimal_jpeg()
        injected = _inject_exif_photo_id(jpeg, "Dwu85P9-SOIk")
        assert _extract_exif_photo_id(injected) == "Dwu85P9-SOIk"

    def test_non_jpeg_passthrough(self):
        png_bytes = b"\x89PNG\r\n\x1a\nsome data"
        result = _inject_exif_photo_id(png_bytes, "abc123")
        assert result == png_bytes  # unchanged

    def test_empty_bytes_passthrough(self):
        result = _inject_exif_photo_id(b"", "abc123")
        assert result == b""

    def test_still_valid_jpeg(self):
        jpeg = _minimal_jpeg()
        injected = _inject_exif_photo_id(jpeg, "test-id")
        assert injected[0:2] == b"\xff\xd8"  # still starts with JPEG SOI


class TestExtractExifPhotoId:
    def test_no_exif(self):
        jpeg = _minimal_jpeg()
        assert _extract_exif_photo_id(jpeg) is None

    def test_non_jpeg(self):
        assert _extract_exif_photo_id(b"\x89PNG\r\n\x1a\n") is None

    def test_empty_bytes(self):
        assert _extract_exif_photo_id(b"") is None


class TestWithUtmParams:
    def test_appends_when_no_query(self):
        result = _with_utm_params("https://unsplash.com/photos/abc123")
        assert result == (
            "https://unsplash.com/photos/abc123?"
            "utm_source=unsplash_mcp&utm_medium=referral"
        )

    def test_appends_when_existing_query(self):
        result = _with_utm_params("https://unsplash.com/@jane?foo=bar")
        assert result == (
            "https://unsplash.com/@jane?foo=bar&"
            "utm_source=unsplash_mcp&utm_medium=referral"
        )


class TestBuildAttributionMarkdown:
    def test_format_and_links(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane Smith",
            photographer_profile_url="https://unsplash.com/@janesmith",
            description="A mountain landscape",
            alt_description="snow-capped mountains",
        )
        assert result == (
            '"[A mountain landscape]'
            "(https://unsplash.com/photos/abc123?"
            'utm_source=unsplash_mcp&utm_medium=referral)" '
            "by [Jane Smith]"
            "(https://unsplash.com/@janesmith?"
            "utm_source=unsplash_mcp&utm_medium=referral) "
            "on [Unsplash]"
            "(https://unsplash.com?"
            "utm_source=unsplash_mcp&utm_medium=referral)"
        )

    def test_falls_back_to_alt_description(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description=None,
            alt_description="a cat",
        )
        assert '"[a cat](https://unsplash.com/photos/abc123?' in result

    def test_falls_back_to_untitled(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description=None,
            alt_description=None,
        )
        assert '"[Untitled]' in result

    def test_photo_id_used_in_url(self):
        result = _build_attribution_markdown(
            photo_id="Dwu85P9-SOIk",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
        )
        assert "https://unsplash.com/photos/Dwu85P9-SOIk?" in result

    def test_newlines_in_description_flattened(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description="line one\nline two\r\nline three",
        )
        assert '"[line one line two  line three]' in result
        assert "\n" not in result

    def test_whitespace_only_description_falls_back_to_untitled(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description="   \n  ",
            alt_description=None,
        )
        assert '"[Untitled]' in result

    def test_whitespace_only_description_falls_back_to_alt_description(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description="   \n  ",
            alt_description="a cat",
        )
        assert '"[a cat]' in result

    def test_brackets_in_description_escaped(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane",
            photographer_profile_url="https://unsplash.com/@jane",
            description="Title with [brackets]",
        )
        assert r"\[brackets\]" in result

    def test_brackets_in_photographer_name_escaped(self):
        result = _build_attribution_markdown(
            photo_id="abc123",
            photographer_name="Jane [Doe]",
            photographer_profile_url="https://unsplash.com/@jane",
            description="A photo",
        )
        assert r"Jane \[Doe\]" in result


class TestGetPhotoIdFromExif:
    @pytest.mark.anyio
    async def test_valid_file(self, tmp_path):
        from server import get_photo_id_from_exif

        jpeg = _inject_exif_photo_id(_minimal_jpeg(), "abc123")
        temp_file = tmp_path / "photo.jpg"
        temp_file.write_bytes(jpeg)

        result = await get_photo_id_from_exif(str(temp_file))
        assert result == "abc123"

    @pytest.mark.anyio
    async def test_no_exif_in_file(self, tmp_path):
        from server import get_photo_id_from_exif

        temp_file = tmp_path / "plain.jpg"
        temp_file.write_bytes(_minimal_jpeg())

        with pytest.raises(ToolError, match="No Unsplash photo ID found in EXIF"):
            await get_photo_id_from_exif(str(temp_file))

    @pytest.mark.anyio
    async def test_file_not_found(self):
        from server import get_photo_id_from_exif

        with pytest.raises(ToolError, match="File does not exist or is not a file"):
            await get_photo_id_from_exif("/tmp/nonexistent_file_12345.jpg")


class TestValidatePhotoId:
    def test_valid_simple(self):
        assert _validate_photo_id("abc123") == "abc123"

    def test_valid_with_hyphens(self):
        assert _validate_photo_id("Dwu85P9-SOIk") == "Dwu85P9-SOIk"

    def test_valid_with_underscores(self):
        assert _validate_photo_id("abc_123") == "abc_123"

    def test_strips_whitespace(self):
        assert _validate_photo_id("  abc123  ") == "abc123"

    def test_empty_string(self):
        with pytest.raises(ValueError, match="photo_id must not be empty"):
            _validate_photo_id("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="photo_id must not be empty"):
            _validate_photo_id("   ")

    def test_path_traversal(self):
        with pytest.raises(ValueError, match="Invalid photo_id"):
            _validate_photo_id("../etc/passwd")

    def test_special_characters(self):
        with pytest.raises(ValueError, match="Invalid photo_id"):
            _validate_photo_id("abc;rm -rf /")


class TestSearchPhotosValidation:
    @pytest.mark.anyio
    async def test_empty_query(self):
        from server import search_photos

        with pytest.raises(ValueError, match="query must not be empty"):
            await search_photos(query="")

    @pytest.mark.anyio
    async def test_whitespace_query(self):
        from server import search_photos

        with pytest.raises(ValueError, match="query must not be empty"):
            await search_photos(query="   ")

    @pytest.mark.anyio
    async def test_invalid_order_by(self):
        from server import search_photos

        with pytest.raises(ValueError, match="Invalid order_by"):
            await search_photos(query="mountain", order_by="invalid")

    @pytest.mark.anyio
    async def test_invalid_color(self):
        from server import search_photos

        with pytest.raises(ValueError, match="Invalid color"):
            await search_photos(query="mountain", color="rainbow")

    @pytest.mark.anyio
    async def test_invalid_orientation(self):
        from server import search_photos

        with pytest.raises(ValueError, match="Invalid orientation"):
            await search_photos(query="mountain", orientation="diagonal")
