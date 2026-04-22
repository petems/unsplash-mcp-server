# VHS tape — re-runnable terminal demo for the Unsplash MCP server.
# Regenerate with: make demo   (requires `brew install vhs`)
# This tape runs the fixture-backed docs/demo/demo_client.py, so it needs no
# real UNSPLASH_ACCESS_KEY and produces a deterministic GIF on every run.

Output docs/demo.gif

Require uv

Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Framerate 30

Env UNSPLASH_MCP_DEMO_MODE "1"
Env UNSPLASH_ACCESS_KEY "demo-mode-no-real-key"

# Setup — hidden from the recording.
Hide
Type "cd $(git rev-parse --show-toplevel) && rm -rf /tmp/demo && clear"
Enter
Sleep 1s
Show

Sleep 500ms
Type "uv run python docs/demo/demo_client.py"
Sleep 400ms
Enter
Sleep 14s
