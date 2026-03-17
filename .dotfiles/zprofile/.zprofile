#!/usr/bin/env zsh
#
# PATH
export PATH="$HOME/.local/share/bob/nvim-bin:$HOME/.local/bin:$PATH"

# NVM setup
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Podman rootless socket (WSL2 workaround)
[ -S "/run/user/${UID}/podman/podman.sock" ] && \
    export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock

### OMZ ###
export ZSH="$HOME/.oh-my-zsh"

