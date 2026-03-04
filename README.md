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

## License

[MIT License](LICENSE)
