# Demo recording

The `docs/demo.gif` shown in the top-level README is produced by this folder.

## Regenerating the GIF

```sh
brew install vhs   # one-time (pulls ttyd + ffmpeg)
make demo          # renders docs/demo.gif from docs/demo/demo.tape
```

No real Unsplash API key is needed. The client spawns `demo_server.py` as
an MCP subprocess over stdio and communicates via JSON-RPC — the same way
Claude Code or MCP Inspector would. When `UNSPLASH_MCP_DEMO_MODE=1` (the
default when launched from the client), the server monkey-patches
`httpx.AsyncClient.get` to return canned responses from `fixtures/`
instead of calling the live Unsplash API. Deterministic and secret-free.

```
demo_client.py  ──stdio JSON-RPC──▶  demo_server.py (patched httpx)
                                          │
                                          ▼
                                     fixtures/*.json
```

## Files

- `demo.tape` — VHS script (source of truth for the recording)
- `demo_client.py` — MCP client; spawns `demo_server.py` as a subprocess
  and calls tools via `fastmcp.Client`
- `demo_server.py` — stdio MCP entrypoint that installs the httpx fixture
  patch and then runs the real `server.mcp`
- `fixtures/search_mountain.json` — response for `GET /search/photos`
- `fixtures/photo_meta.json` — response for `GET /photos/{id}`
- `fixtures/image_regular.bin` — tiny valid JPEG returned for image CDN URLs

## Refreshing fixtures

The fixtures are hand-authored to look like real Unsplash responses but are
not real. If the server's request shape or response parsing changes, update
the fixtures to match. The minimum schema each one needs mirrors the fields
`server.py` reads — adding or removing fields elsewhere is fine.
