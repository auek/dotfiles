#!/usr/bin/env zsh
#
# PATH
typeset -U path PATH
path=("$HOME/.local/bin" $path)
export PATH

# Shims make managed tools available to login commands without an interactive prompt.
if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate zsh --shims)"
fi

# Preferred editor
if command -v nvim >/dev/null 2>&1; then
  export EDITOR="nvim"
  export VISUAL="nvim"
elif command -v vim >/dev/null 2>&1; then
  export EDITOR="vim"
  export VISUAL="vim"
fi

# Opt-in graphical session after a local Arch login on tty1. The guards keep
# SSH, other virtual terminals, and shells launched inside Hyprland unchanged.
if grep -qx 'ID=arch' /etc/os-release 2>/dev/null && \
    [[ -f "$HOME/.local/state/dotfiles/hyprland/autostart" ]] && \
    [[ -z "${SSH_CONNECTION:-}" && -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]] && \
    [[ "${XDG_VTNR:-}" == "1" ]] && \
    command -v start-hyprland >/dev/null 2>&1; then
  exec start-hyprland
fi

# Podman rootless socket (WSL2 workaround only)
if grep -qi microsoft /proc/version 2>/dev/null; then
  [ -S "/run/user/${UID}/podman/podman.sock" ] && \
      export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
fi
