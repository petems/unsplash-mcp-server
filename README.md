# Unsplash MCP Server

> A simple MCP server for searching Unsplash images.

Fork of [hellokaton/unsplash-mcp-server](https://github.com/hellokaton/unsplash-mcp-server).

![Demo](docs/demo.gif)

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

### download_photo

Download an Unsplash photo by ID and save it to a local file. This tool fetches the image from Unsplash's CDN and writes it directly to disk.

```json
{
  "tool": "download_photo",
  "photo_id": "abc123",
  "save_path": "/absolute/path/to/image.jpg",
  "size": "regular"
}
```

**Parameters:**
- `photo_id` (required): The Unsplash photo ID (obtained from `search_photos` results)
- `save_path` (required): Absolute file path where the image will be saved. If a file already exists at this path, an error will be raised to prevent accidental overwrites.
- `size` (optional): Image size variant — `raw`, `full`, `regular` (default), `small`, or `thumb`
  - `raw`: Original unprocessed image (largest file size)
  - `full`: Full-size processed image (high quality)
  - `regular`: Standard web size (~1080px width, recommended for most uses)
  - `small`: Smaller preview (~400px width)
  - `thumb`: Thumbnail (~200px width)
- `create_directories` (optional): If `true`, automatically create parent directories if they don't exist. Defaults to `false` for safety.

**Returns:**
A structured result containing the photo ID, final save path, size variant, byte count, and a ready-to-use Markdown attribution line.

**Example response:**
```json
{
  "photo_id": "abc123",
  "path": "/home/user/images/mountain_unsplash-abc123.jpg",
  "size": "regular",
  "byte_count": 245891,
  "attribution": "\"[A mountain landscape](https://unsplash.com/photos/abc123?utm_source=unsplash_mcp&utm_medium=referral)\" by [Jane Smith](https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=unsplash_mcp&utm_medium=referral)"
}
```

**Important Notes:**
- The tool automatically triggers Unsplash's download tracking endpoint as required by the [Unsplash API Guidelines](https://help.unsplash.com/en/articles/2511258-guideline-triggering-a-download)
- By default, parent directories must exist; set `create_directories=true` to create them automatically
- The tool uses a 60-second timeout for regular downloads and 120 seconds for `raw` and `full` sizes to accommodate larger files
- **The tool will not overwrite existing files**. If a file already exists at the specified path, an error will be raised asking you to choose a different path or delete the existing file first
- Downloaded images should be used in compliance with the [Unsplash License](https://unsplash.com/license)

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
  "attribution_markdown": "\"[A mountain landscape at sunset](https://unsplash.com/photos/abc123?utm_source=unsplash_mcp&utm_medium=referral)\" by [Jane Smith](https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=unsplash_mcp&utm_medium=referral)"
}
```

The `attribution_markdown` field renders as:

```markdown
"[A mountain landscape at sunset](https://unsplash.com/photos/abc123?utm_source=unsplash_mcp&utm_medium=referral)" by [Jane Smith](https://unsplash.com/@janesmith?utm_source=unsplash_mcp&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=unsplash_mcp&utm_medium=referral)
```

The same `attribution` field is returned as part of each `search_photos` result and the `download_photo` response.

## Regenerating the demo GIF

The animated demo at the top of this README is produced by a [VHS](https://github.com/charmbracelet/vhs) tape that exercises the MCP tools against committed fixtures (no Unsplash key required).

```sh
brew install vhs     # one-time
make demo            # renders docs/demo.gif from docs/demo/demo.tape
```

See [`docs/demo/README.md`](docs/demo/README.md) for details.

## License

[MIT License](LICENSE)
