# -*- coding: utf-8 -*-
"""Tests for Unsplash MCP server photo ID embedding and extraction."""

from pathlib import Path

import pytest

from server import _embed_photo_id_in_path, _extract_photo_id_from_path


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

        with pytest.raises(ValueError, match="No Unsplash photo ID found"):
            await get_photo_id_from_filename(str(temp_file))

    @pytest.mark.anyio
    async def test_file_not_found(self):
        from server import get_photo_id_from_filename

        with pytest.raises(ValueError, match="File does not exist"):
            await get_photo_id_from_filename("/tmp/nonexistent_file_12345.jpg")
