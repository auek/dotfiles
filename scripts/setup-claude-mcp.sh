#!/usr/bin/env bash
# Register user-scoped MCP servers for Claude Code.
# Claude Code reads user MCP servers from ~/.claude.json, not settings.json,
# so they are registered via the CLI. Safe to re-run.
set -euo pipefail

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
BASE="exec npx -y @playwright/mcp@latest --executable-path /usr/bin/chromium --user-data-dir \"\$HOME/.local/share/playwright-mcp/profile\" --user-agent \"$UA\""

add() { # name, shell command
  claude mcp remove --scope user "$1" >/dev/null 2>&1 || true
  claude mcp add-json --scope user "$1" \
    "$(jq -nc --arg c "$2" '{type:"stdio",command:"sh",args:["-c",$c]}')"
}

add playwright "$BASE --headless"
add playwright-headed "$BASE"

# Context7: same API key file as opencode, read when the server starts so the
# key is never copied into ~/.claude.json.
add context7 'exec npx -y @upstash/context7-mcp@latest --api-key "$(cat "$HOME/.secrets/context7-api-key")"'
