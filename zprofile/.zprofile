#!/usr/bin/env zsh
#
# PATH
export PATH="$HOME/.local/share/bob/nvim-bin:$HOME/.local/bin:$PATH"

# Preferred editor
if command -v nvim >/dev/null 2>&1; then
  export EDITOR="nvim"
  export VISUAL="nvim"
elif command -v vim >/dev/null 2>&1; then
  export EDITOR="vim"
  export VISUAL="vim"
fi

# NVM setup
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Podman rootless socket (WSL2 workaround)
[ -S "/run/user/${UID}/podman/podman.sock" ] && \
    export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
