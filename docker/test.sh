#!/usr/bin/env bash
# Run one setup profile twice in a freshly recreated container and assert its baseline.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yml"
DISTRO="arch"
PROFILE="server"

usage() {
  echo "Usage: $0 [-d arch|fedora|ubuntu] [-p server|slim|full]"
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
    *)
      usage
      ;;
  esac
done

case "$DISTRO" in arch|fedora|ubuntu) ;; *) usage ;; esac
case "$PROFILE" in server|slim|full) ;; *) usage ;; esac

SERVICE="dotfiles-$DISTRO"
compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

run() {
  compose exec -T "$SERVICE" bash -lc "$1"
}

compose rm -sf "$SERVICE" >/dev/null 2>&1 || true
compose up -d --build "$SERVICE"

run "bash /home/devuser/code/dotfiles/setup.sh --$PROFILE"
run "bash /home/devuser/code/dotfiles/setup.sh --$PROFILE"

run 'command -v curl git make stow tmux vim'

if [ "$PROFILE" = "server" ]; then
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
  run 'command -v fastfetch gh gcc pipx python3 ssh-agent ssh-add stow tmux unzip zsh'
  run 'test "$(readlink -f "$(getent passwd devuser | cut -d: -f7)")" = "$(readlink -f "$(command -v zsh)")"'
  run 'test "$(readlink -f "$HOME/.zshrc")" = /home/devuser/code/dotfiles/packages/zshrc/.zshrc'
  run 'zsh -lic exit'
fi

if [ "$PROFILE" = "full" ]; then
  run 'command -v eza fd fzf htop bat rg ssh sqlite3 fastfetch nvim'
  run 'zsh -lic "command -v node npm npx uv tldr llm"'
fi

echo "[test] $DISTRO $PROFILE passed"
