#!/usr/bin/env bash
# Install the tested recovery plugins without changing existing checkouts.
set -euo pipefail

plugins="$HOME/.local/share/tmux/plugins"
staging=""
trap 'if [ -n "$staging" ]; then rm -rf -- "$staging"; fi' EXIT

install_plugin() {
  local name="$1" revision="$2" entrypoint="$3" destination
  destination="$plugins/$name"
  if [ -e "$destination" ] || [ -L "$destination" ]; then
    printf '[tmux] Keeping existing %s (no checkout or update)\n' "$destination"
    if [ ! -x "$destination/$entrypoint" ]; then
      printf '[tmux] Warning: missing executable %s; inspect the existing installation\n' \
        "$destination/$entrypoint" >&2
    fi
    return
  fi

  mkdir -p "$plugins"
  staging="$(mktemp -d "$plugins/.$name.XXXXXX")"
  git init -q "$staging"
  git -C "$staging" remote add origin "https://github.com/tmux-plugins/$name.git"
  git -C "$staging" fetch --depth=1 origin "$revision"
  git -C "$staging" checkout -q --detach FETCH_HEAD
  test -x "$staging/$entrypoint"
  # Never replace a path created while the download was in progress.
  mv -T -n "$staging" "$destination"
  if [ -d "$staging" ]; then
    printf '[tmux] Installation destination appeared: %s; leaving it untouched\n' "$destination" >&2
    exit 1
  fi
  staging=""
  printf '[tmux] Installed %s at %s\n' "$name" "$revision"
}

install_plugin tmux-resurrect cff343cf9e81983d3da0c8562b01616f12e8d548 resurrect.tmux
install_plugin tmux-continuum 0698e8f4b17d6454c71bf5212895ec055c578da0 continuum.tmux

# Snapshots are private local state, never Stow-managed or moved on upgrade.
if [ ! -e "$HOME/.local/state/tmux/resurrect" ]; then
  install -d -m 0700 "$HOME/.local/state/tmux/resurrect"
fi
