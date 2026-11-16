#!/usr/bin/env bash
# Merge the repo's Claude Code settings baseline into ~/.claude/settings.json.
# Claude Code rewrites that file whenever a setting changes (theme, tui, ...),
# so it must be a real, machine-local file, not a link into the repo. Keys in
# packages/claude/settings.base.json win; other keys are kept. Safe to re-run.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base=$root/packages/claude/settings.base.json
dest=${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}

mkdir -p "$(dirname "$dest")"
current='{}'
# Read through an old Stow link first so its content survives the switch.
# A dangling link (the repo file moved) simply starts from the baseline.
if [ -f "$dest" ]; then current=$(cat "$dest"); fi
tmp=$(mktemp "$dest.XXXXXX")
trap 'rm -f "$tmp"' EXIT
jq -n --argjson local "$current" --slurpfile base "$base" '$local * $base[0]' >"$tmp"
if [ -L "$dest" ] || ! cmp -s "$tmp" "$dest"; then
  mv "$tmp" "$dest"
fi
