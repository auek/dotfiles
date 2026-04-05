#!/usr/bin/env bash

set -euo pipefail

SCHEMA="org.gnome.desktop.input-sources"
KEY="xkb-options"
VALUE="['compose:menu']"

if ! command -v gsettings >/dev/null 2>&1; then
  echo "[compose] gsettings not available; skipping Compose key setup"
  exit 0
fi

if ! gsettings writable "$SCHEMA" "$KEY" >/dev/null 2>&1; then
  echo "[compose] GNOME input source settings not writable here; skipping Compose key setup"
  exit 0
fi

current="$(gsettings get "$SCHEMA" "$KEY")"

if [ "$current" = "$VALUE" ]; then
  echo "[compose] Compose key already set to Menu"
  exit 0
fi

gsettings set "$SCHEMA" "$KEY" "$VALUE"
echo "[compose] Set Compose key to Menu"
