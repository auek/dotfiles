#!/usr/bin/env bash
#
# configure-gnome-keybindings.sh — Apply GNOME keyboard preferences
#
# Called by setup.sh during bootstrap. Safe to re-run (idempotent).
# Skips silently when gsettings is unavailable (e.g. headless / non-GNOME).

set -euo pipefail

# ─── Guard ────────────────────────────────────────────────────────────────────

if ! command -v gsettings >/dev/null 2>&1; then
  echo "[keybindings] gsettings not available; skipping"
  exit 0
fi

# Quick writability probe using a well-known key
if ! gsettings writable org.gnome.desktop.input-sources xkb-options >/dev/null 2>&1; then
  echo "[keybindings] GNOME settings not writable here; skipping"
  exit 0
fi

# ─── Input sources ────────────────────────────────────────────────────────────
# Set the right Alt key as the Compose key so that sequences like
# RightAlt + , + c → ç work without a dedicated Compose key on the keyboard.

COMPOSE_SCHEMA="org.gnome.desktop.input-sources"
COMPOSE_KEY="xkb-options"
COMPOSE_VALUE="['compose:ralt']"

current_compose="$(gsettings get "$COMPOSE_SCHEMA" "$COMPOSE_KEY")"

if [ "$current_compose" = "$COMPOSE_VALUE" ]; then
  echo "[keybindings] Compose key already set to RAlt"
else
  gsettings set "$COMPOSE_SCHEMA" "$COMPOSE_KEY" "$COMPOSE_VALUE"
  echo "[keybindings] Set Compose key to RAlt"
fi

# ─── Custom shortcuts ─────────────────────────────────────────────────────────
# GNOME stores custom shortcuts as an array of dconf paths. Each path has its
# own name/command/binding sub-keys. We append a new slot only if a kitty
# shortcut does not already exist.

MEDIA_KEYS="org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_BASE="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

# Read the current list of custom shortcut paths (looks like @as [] or
# ['/path/custom0/', '/path/custom1/', ...])
current_list="$(gsettings get "$MEDIA_KEYS" custom-keybindings)"

# Check whether any existing slot already has command 'kitty'
already_set=0
# Strip brackets/quotes/spaces to get bare path segments
for path in $(echo "$current_list" | tr -d "[]' " | tr ',' '\n'); do
  [ -z "$path" ] && continue
  cmd="$(gsettings get "${MEDIA_KEYS}.custom-keybinding:${path}" command 2>/dev/null || true)"
  if [ "$cmd" = "'kitty'" ]; then
    already_set=1
    break
  fi
done

if [ "$already_set" -eq 1 ]; then
  echo "[keybindings] Kitty shortcut (Ctrl+Alt+T) already configured"
else
  # Find the first unused slot name (custom0, custom1, ...)
  index=0
  while echo "$current_list" | grep -q "custom${index}/"; do
    index=$((index + 1))
  done
  new_path="${CUSTOM_BASE}/custom${index}/"

  # Build the updated array: append the new path
  if [ "$current_list" = "@as []" ] || [ "$current_list" = "[]" ]; then
    new_list="['${new_path}']"
  else
    # Insert before the closing bracket
    new_list="${current_list%]}, '${new_path}']"
  fi

  gsettings set "$MEDIA_KEYS" custom-keybindings "$new_list"
  gsettings set "${MEDIA_KEYS}.custom-keybinding:${new_path}" name    'Open Kitty'
  gsettings set "${MEDIA_KEYS}.custom-keybinding:${new_path}" command 'kitty'
  gsettings set "${MEDIA_KEYS}.custom-keybinding:${new_path}" binding '<Primary><Alt>t'

  echo "[keybindings] Added Kitty shortcut: Ctrl+Alt+T → kitty (slot: custom${index})"
fi
