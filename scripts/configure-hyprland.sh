#!/usr/bin/env bash
# Called by setup.sh --hyprland after the desktop packages have been linked.
set -euo pipefail

config="$HOME/.config/hypr/hyprland.lua"
state="$HOME/.local/state/dotfiles/hyprland"
mkdir -p "$(dirname "$config")" "$state"

# noclobber also protects an existing dangling symlink or a concurrent writer.
if [ -e "$config" ] || [ -L "$config" ]; then
  printf '[setup] Preserving existing %s; it should load require("dotfiles")\n' "$config"
else
  (set -o noclobber; printf 'require("dotfiles")\n' > "$config")
fi

# This is local runtime state, not a tracked machine preference.
touch "$state/autostart"

if command -v systemctl >/dev/null 2>&1 && systemctl --user daemon-reload; then
  printf '[setup] Hyprland user units registered\n'
else
  printf '[setup] User service manager unavailable; run systemctl --user daemon-reload before your first Hyprland session\n'
fi
