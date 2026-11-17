#!/usr/bin/env bash
# Register user-scoped MCP servers for Claude Code.
# Claude Code reads user MCP servers from ~/.claude.json, not settings.json,
# so they are registered via the CLI. Safe to re-run.
#
# Usage: setup-claude-mcp.sh [--headless-only]
#   --headless-only  Register only the headless Playwright server (servers).
#                    Without it, the headed server is registered too, but it is
#                    skipped with a warning when no display is available.
set -euo pipefail

HEADLESS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --headless-only) HEADLESS_ONLY=1 ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "setup-claude-mcp: unknown option: $arg" >&2; exit 2 ;;
  esac
done

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
BASE="exec npx -y @playwright/mcp@latest"
# Use the system Chromium when present; otherwise Playwright falls back to its
# own managed browser (npx playwright install chromium).
if [ -x /usr/bin/chromium ]; then
  BASE="$BASE --executable-path /usr/bin/chromium"
fi
BASE="$BASE --user-data-dir \"\$HOME/.local/share/playwright-mcp/profile\" --user-agent \"$UA\""

add() { # name, shell command
  claude mcp remove --scope user "$1" >/dev/null 2>&1 || true
  claude mcp add-json --scope user "$1" \
    "$(jq -nc --arg c "$2" '{type:"stdio",command:"sh",args:["-c",$c]}')"
}

add playwright "$BASE --headless"

if [ "$HEADLESS_ONLY" -eq 1 ]; then
  echo "setup-claude-mcp: --headless-only, not registering playwright-headed"
elif [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  echo "setup-claude-mcp: no DISPLAY or WAYLAND_DISPLAY, skipping playwright-headed" >&2
  echo "  (pass --headless-only to silence this on servers)" >&2
else
  add playwright-headed "$BASE"
fi

# Context7: same API key file as opencode, read when the server starts so the
# key is never copied into ~/.claude.json. Skipped when the key is absent.
if [ -r "$HOME/.secrets/context7-api-key" ]; then
  add context7 'exec npx -y @upstash/context7-mcp@latest --api-key "$(cat "$HOME/.secrets/context7-api-key")"'
else
  echo "setup-claude-mcp: ~/.secrets/context7-api-key not found, skipping context7" >&2
fi
