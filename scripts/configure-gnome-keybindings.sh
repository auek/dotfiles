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
# Use the built-in Swedish (US) XKB variant so Right Alt behaves like AltGr on
# the Swedish punctuation positions: RAlt+[ => å, RAlt+; => ö, RAlt+' => ä.

INPUT_SCHEMA="org.gnome.desktop.input-sources"
INPUT_SOURCES_KEY="sources"
INPUT_OPTIONS_KEY="xkb-options"
INPUT_SOURCE_VALUE="[('xkb', 'se+us')]"

current_sources="$(gsettings get "$INPUT_SCHEMA" "$INPUT_SOURCES_KEY")"

if [ "$current_sources" = "$INPUT_SOURCE_VALUE" ]; then
  echo "[keybindings] Keyboard layout already set to Swedish (US)"
else
  gsettings set "$INPUT_SCHEMA" "$INPUT_SOURCES_KEY" "$INPUT_SOURCE_VALUE"
  echo "[keybindings] Set keyboard layout to Swedish (US)"
fi

current_options="$(gsettings get "$INPUT_SCHEMA" "$INPUT_OPTIONS_KEY")"
filtered_options=()

for option in $(echo "$current_options" | tr -d "[]' " | tr ',' '\n'); do
  [ -z "$option" ] && continue
  case "$option" in
    compose:*) ;;
    *) filtered_options+=("$option") ;;
  esac
done

if [ "${#filtered_options[@]}" -eq 0 ]; then
  case "$current_options" in
    "[]"|"@as []") filtered_options_value="$current_options" ;;
    *) filtered_options_value="[]" ;;
  esac
else
  filtered_options_value="["
  for option in "${filtered_options[@]}"; do
    if [ "$filtered_options_value" != "[" ]; then
      filtered_options_value+=", "
    fi
    filtered_options_value+="'${option}'"
  done
  filtered_options_value+="]"
fi

if [ "$current_options" = "$filtered_options_value" ]; then
  echo "[keybindings] No Compose key option configured"
else
  gsettings set "$INPUT_SCHEMA" "$INPUT_OPTIONS_KEY" "$filtered_options_value"
  echo "[keybindings] Removed Compose key option to keep RAlt available for AltGr"
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
