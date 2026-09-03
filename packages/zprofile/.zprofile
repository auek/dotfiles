#!/usr/bin/env zsh
#
# PATH
export PATH="$HOME/.local/bin:$PATH"

# Bob supplies current Neovim on Ubuntu/Debian; other supported distros use
# their native Neovim package.
if [[ -x "$HOME/.local/state/bob/nvim-bin/nvim" ]] && \
    grep -qE '^ID=(ubuntu|debian)$' /etc/os-release 2>/dev/null; then
  export PATH="$HOME/.local/state/bob/nvim-bin:$PATH"
fi

# Preferred editor
if command -v nvim >/dev/null 2>&1; then
  export EDITOR="nvim"
  export VISUAL="nvim"
elif command -v vim >/dev/null 2>&1; then
  export EDITOR="vim"
  export VISUAL="vim"
fi

# Podman rootless socket (WSL2 workaround only)
if grep -qi microsoft /proc/version 2>/dev/null; then
  [ -S "/run/user/${UID}/podman/podman.sock" ] && \
      export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
fi
