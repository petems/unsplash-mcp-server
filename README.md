# Unsplash MCP Server

> A simple MCP server for searching Unsplash images.

Fork of [hellokaton/unsplash-mcp-server](https://github.com/hellokaton/unsplash-mcp-server).

## Overview

Unsplash MCP Server provides tools for searching Unsplash's library of high-quality images. It supports filtering by keyword, color, orientation, and pagination.

## Obtaining an Unsplash Access Key

1. Create a developer account at [Unsplash](https://unsplash.com/developers)
2. Register a new application
3. Get your Access Key from the application details page

For more details, refer to the [official Unsplash API documentation](https://unsplash.com/documentation).

## Installation

### Claude Code

Add the following to your `~/.claude.json` (user scope) or `.mcp.json` in your project root (project scope):

```json
{
  "mcpServers": {
    "unsplash": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/petems/unsplash-mcp-server", "unsplash-mcp-server"],
      "env": {
        "UNSPLASH_ACCESS_KEY": "your_access_key"
      }
    }
  }
}
```

### Manual Installation

```bash
git clone https://github.com/petems/unsplash-mcp-server.git
cd unsplash-mcp-server
uv venv
uv pip install .
```

## Available Tools

### search_photos

Search Unsplash's photo library with optional filters.

```json
{
  "tool": "search_photos",
  "query": "mountain",
  "per_page": 5,
  "orientation": "landscape"
}
```

### get_photo_attribution

Returns properly formatted attribution for an Unsplash photo, compliant with Unsplash API guidelines. Includes both structured data (JSON) and a ready-to-use Markdown string.

```json
{
  "tool": "get_photo_attribution",
  "photo_id": "abc123",
  "image_size": "regular"
}
```

**Parameters:**
- `photo_id` (required): The unique identifier of the Unsplash photo
- `image_size` (optional): Size of image URL to use — `raw`, `full`, `regular` (default), `small`, or `thumb`

**Example response:**

```json
{
  "photo_id": "abc123",
  "description": "A mountain landscape at sunset",
  "alt_description": "snow-capped mountains under orange sky",
  "photo_url": "https://unsplash.com/photos/abc123?utm_source=unsplash_mcp&utm_medium=referral",
  "image_url": "https://images.unsplash.com/photo-abc123?w=1080",
  "photographer_name": "Jane Smith",
  "photographer_url": "https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral",
  "attribution_markdown": "![snow-capped mountains under orange sky](https://images.unsplash.com/photo-abc123?w=1080)\n*Photo by [Jane Smith](https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=unsplash_mcp&utm_medium=referral)*"
}
```

The `attribution_markdown` field renders as:

```markdown
![snow-capped mountains under orange sky](https://images.unsplash.com/photo-abc123?w=1080)
*Photo by [Jane Smith](https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=unsplash_mcp&utm_medium=referral)*
```

## License

[MIT License](LICENSE)
