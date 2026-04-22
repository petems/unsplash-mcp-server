# Demo recording

The `docs/demo.gif` shown in the top-level README is produced by this folder.

## Regenerating the GIF

```sh
brew install vhs   # one-time (pulls ttyd + ffmpeg)
make demo          # renders docs/demo.gif from docs/demo/demo.tape
```

No real Unsplash API key is needed. The tape sets `UNSPLASH_MCP_DEMO_MODE=1`,
which tells `demo_client.py` to monkey-patch `httpx.AsyncClient.get` and
return canned responses from `fixtures/` instead of calling the live API.
This keeps the recording deterministic and secret-free.

## Files

- `demo.tape` — VHS script (source of truth for the recording)
- `demo_client.py` — async driver that calls the MCP tools and pretty-prints
- `fixtures/search_mountain.json` — response for `GET /search/photos`
- `fixtures/photo_meta.json` — response for `GET /photos/{id}`
- `fixtures/image_regular.bin` — tiny valid JPEG returned for image CDN URLs

## Refreshing fixtures

The fixtures are hand-authored to look like real Unsplash responses but are
not real. If the server's request shape or response parsing changes, update
the fixtures to match. The minimum schema each one needs mirrors the fields
`server.py` reads — adding or removing fields elsewhere is fine.
