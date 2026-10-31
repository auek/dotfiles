#!/usr/bin/env bash
# Run one setup profile twice in a freshly recreated container and assert its baseline.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yml"
DISTRO="arch"
PROFILE="server"
HYPRLAND=""

usage() {
  echo "Usage: $0 [-d arch|fedora|ubuntu] [-p server|slim|full] [--hyprland]"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -d|--distro)
      DISTRO="${2:-}"
      shift 2
      ;;
    -p|--profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    --hyprland)
      HYPRLAND="--hyprland"
      shift
      ;;
    *)
      usage
      ;;
  esac
done

case "$DISTRO" in arch|fedora|ubuntu) ;; *) usage ;; esac
case "$PROFILE" in server|slim|full) ;; *) usage ;; esac
if [ -n "$HYPRLAND" ] && { [ "$DISTRO" != "arch" ] || [ "$PROFILE" = "server" ]; }; then
  usage
fi

SERVICE="dotfiles-$DISTRO"
compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

run() {
  compose exec -T "$SERVICE" bash -lc "$1"
}

require_commands() {
  local command_name

  for command_name in "$@"; do
    run "command -v $command_name >/dev/null"
  done
}

require_zsh_commands() {
  local command_name

  for command_name in "$@"; do
    run "zsh -lic 'command -v $command_name >/dev/null'"
  done
}

compose rm -sf "$SERVICE" >/dev/null 2>&1 || true
compose up -d --build "$SERVICE"

run "bash /home/devuser/code/dotfiles/setup.sh --$PROFILE $HYPRLAND"
if [ -n "$HYPRLAND" ]; then
  # Seed a local customization to verify that a repeat bootstrap preserves it.
  run 'printf "\n-- local customization\n" >> "$HOME/.config/hypr/hyprland.lua"'
fi
run "bash /home/devuser/code/dotfiles/setup.sh --$PROFILE $HYPRLAND"

require_commands curl git make stow tmux

if [ "$PROFILE" = "server" ]; then
  require_commands vim
  run 'test "$(getent passwd devuser | cut -d: -f7)" = /bin/bash'
  run 'test "$(readlink -f "$HOME/.bashrc")" = /home/devuser/code/dotfiles/packages/bashrc-server/.bashrc'
  run 'test "$(readlink -f "$HOME/.vimrc")" = /home/devuser/code/dotfiles/packages/vim-server/.vimrc'
  run 'test "$(readlink -f "$HOME/.tmux.conf")" = /home/devuser/code/dotfiles/packages/tmux-server/.tmux.conf'
  run 'bash -lic exit'
else
  run 'test -d "$HOME/.local/bin" && test ! -L "$HOME/.local/bin"'
  run 'test -d "$HOME/.local/share" && test ! -L "$HOME/.local/share"'
  run 'test -L "$HOME/.local/bin/theme-set"'
  run 'test -f "$HOME/.local/share/dotfiles/themes/everforest/foot.ini"'
  require_commands gh gcc pipx python3 ssh-agent ssh-add stow tmux unzip zsh
  run 'test "$(readlink -f "$(getent passwd devuser | cut -d: -f7)")" = "$(readlink -f "$(command -v zsh)")"'
  run 'test "$(readlink -f "$HOME/.zshrc")" = /home/devuser/code/dotfiles/packages/zshrc/.zshrc'
  run 'zsh -lic exit'
fi

if [ -n "$HYPRLAND" ]; then
  require_commands Hyprland start-hyprland hypridle foot mako waybar wofi swaybg grim slurp wl-copy cliphist playerctl
  run 'test -f "$HOME/.config/hypr/hyprland.lua" && test ! -L "$HOME/.config/hypr/hyprland.lua"'
  run 'grep -qx -- "-- local customization" "$HOME/.config/hypr/hyprland.lua"'
  run 'test -f "$HOME/.local/state/dotfiles/hyprland/autostart"'
  run 'test -L "$HOME/.config/hypr/dotfiles.lua"'
  run 'test -L "$HOME/.config/systemd/user/hyprland-session.target"'
elif [ "$PROFILE" != "server" ]; then
  run 'test ! -e "$HOME/.config/hypr/dotfiles.lua"'
  run 'test ! -e "$HOME/.local/state/dotfiles/hyprland/autostart"'
fi

if [ "$PROFILE" = "full" ]; then
  require_commands htop ssh sqlite3
  require_zsh_commands mise node npm npx nvim bat eza tldr lazygit fastfetch rg fd fzf llm
  run 'zsh -lic '\''test "$(node --version)" = v24.19.0 && mise exec -- nvim --version >/dev/null'\'''
fi

echo "[test] $DISTRO $PROFILE $HYPRLAND passed (bootstrap only; no graphical session)"
