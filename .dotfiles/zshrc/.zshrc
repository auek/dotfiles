#!/usr/bin/env zsh

### Environment / Settings ###
HISTFILE=~/.zsh_history
HISTSIZE=500000
SAVEHIST=500000
setopt appendhistory
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY
unsetopt BEEP

# Case-insensitive completion
autoload -Uz compinit && compinit
zstyle ":completion:*" matcher-list "m:{a-z}={A-Za-z}"

### Oh My Zsh Configuration ###
ZSH_THEME="robbyrussell"
plugins=(git ssh-agent zsh-autosuggestions)

# OMZ Plugin Settings
zstyle ':omz:*' aliases no
zstyle :omz:plugins:ssh-agent identities id_ed25519

source $ZSH/oh-my-zsh.sh

### Binds ###
bindkey "[D" backward-word
bindkey "[C" forward-word
bindkey "^[a" beginning-of-line
bindkey "^[e" end-of-line
bindkey "\e\e[D" backward-word
bindkey "\e\e[C" forward-word

### Functions ###
# Helper function to run commands with secrets loaded only in a subshell
with_secrets() {
  if [ -f ~/.secrets ]; then
    (
      source ~/.secrets
      "$@"
    )
  else
    echo "Error: ~/.secrets file not found."
    return 1
  fi
}

# WSL open function
if grep -qi microsoft /proc/version 2>/dev/null; then
  open() { explorer.exe "${1:-.}"; }
fi

# dev: nvim + aider
if command -v tmux &> /dev/null; then
  function dev() {
    local detach=false
    
    # Parse flags
    while [[ "$1" == "-d" || "$1" == "-h" ]]; do
      if [[ "$1" == "-d" ]]; then
        detach=true
      elif [[ "$1" == "-h" ]]; then
        echo "Usage: dev [-d] <session_name> <project_path>"
        echo "  -d    Start session detached (do not attach)"
        echo "  -h    Show this help message"
        return 0
      fi
      shift
    done
    
    local name=${1:?session name required}
    local dir=${2:?project path required}
    
    if tmux has-session -t "$name" 2>/dev/null; then
      if [ "$detach" = false ]; then
        tmux attach -t "$name"
      fi
    else
      tmux new-session -d -s "$name" -c "$dir"

      if command -v nvim &> /dev/null; then
        tmux send-keys -t "$name" "nvim" Enter
      fi

      if command -v aider &> /dev/null; then
        tmux split-window -h -t "$name" -c "$dir"
        tmux send-keys -t "$name" "with_secrets aider" Enter
      fi

      if [ "$detach" = false ]; then
        tmux attach -t "$name"
      fi
    fi
  }
else
  function dev() {
    echo "Error: tmux is not installed."
  }
fi

### Aliases ###
# General
alias p="pwd"
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../../.."

# Tool-specific
if command -v exa &> /dev/null; then
  alias l="exa"
  alias ls="exa"
  alias ll="exa -lah"
  alias t="exa --all -I .git --icons --classify --sort=type -T -L 2"
fi

if command -v nvim &> /dev/null; then
  alias vim="nvim"
fi

# Git
alias gst="git status"
alias gb="git branch"
alias glg="git log"
alias gp="git push"
alias gpsup="git push -u origin HEAD"
alias gl="git pull"
alias gcane="git commit --amend --no-edit"
alias gcam="git commit -am"
alias gcmsg="git commit -m"
alias gco="git checkout"
alias gcb="git checkout -b"
alias gcm="git checkout main || git checkout master"
alias gc-="git checkout -"

# Secrets-wrapped commands
alias aider='with_secrets aider'
alias llm='with_secrets llm'

# SSH
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)" > /dev/null
  ssh-add 2>/dev/null
fi

### FZF and External Tool Integrations ###
# FZF configuration (only if fd is available)
if command -v fd &> /dev/null; then
  FZF_CMD_ARGS="--hidden --exclude .git --exclude node_modules --exclude .cache --exclude .venv --exclude cache"

  export FZF_DEFAULT_COMMAND="fd --type f $FZF_CMD_ARGS"
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND="fd --type d $FZF_CMD_ARGS"

  # Search directories from home directory (Alt + Shift + C)
  fzf-cd-home() {
    local dir=$(fd --type d --max-depth 5 ${=FZF_CMD_ARGS} . "$HOME" 2>/dev/null | fzf)
    if [ -n "$dir" ]; then
      cd "$dir"
      zle reset-prompt
    fi
  }
  zle -N fzf-cd-home
  bindkey "\eC" fzf-cd-home

  # Check for bat to provide rich previews, otherwise fallback
  if command -v bat &> /dev/null; then
    export FZF_DEFAULT_OPTS='--tmux center --preview "[[ -f {} ]] && bat --color=always --style=header,grid --line-range :500 {} || echo {} is a directory"'
  else
    export FZF_DEFAULT_OPTS='--tmux center --preview "[[ -f {} ]] && head -n 500 {} || echo {} is a directory"'
  fi

  source <(fzf --zsh)
fi

# opencode
export PATH=/home/august/.opencode/bin:$PATH
