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

# Clipboard helper with graceful fallback
_copy() {
  if command -v clip.exe >/dev/null 2>&1; then
    clip.exe
  elif command -v wl-copy >/dev/null 2>&1; then
    wl-copy
  elif command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard
  else
    # Fallback: Just consume the input so the pipe doesn't break
    cat > /dev/null
  fi
}

# dev: nvim + aider OR opencode + terminal
if command -v tmux &> /dev/null; then
  function dev() {
    local attach=true
    local tool="opencode"

    while [[ "$1" == "-d" || "$1" == "-h" ]]; do
      if [[ "$1" == "-d" ]]; then
        attach=false
      elif [[ "$1" == "-h" ]]; then
        echo "Usage: dev [-d] [-h] [aider] <session_name> [<project_path>]"
        echo "  aider          Start session with nvim + aider (default: opencode)"
        echo "  -d             Start session detached (do not attach)"
        echo "  -h             Show this help message"
        return 0
      fi
      shift
    done

    if [[ "$1" == "aider" ]]; then
      tool="aider"
      shift
    fi

    if [[ "$#" -lt 1 ]]; then
      echo "Usage: dev [-d] [-h] [aider] <session_name> [<project_path>]"
      echo "  aider          Start session with nvim + aider (default: opencode)"
      echo "  -d             Start session detached (do not attach)"
      echo "  -h             Show this help message"
      return 1
    fi

    local name=$1
    local dir=$2

    if tmux has-session -t "$name" 2>/dev/null; then
      if [ "$attach" = true ]; then
        if [ -n "$TMUX" ]; then
          tmux switch-client -t "$name"
        else
          tmux attach -t "$name"
        fi
      fi
    else
      if [[ -z "$dir" ]]; then
        echo "Error: project path required to create a new session"
        echo "Usage: dev [-d] [-h] [aider] <session_name> [<project_path>]"
        return 1
      fi
      if [[ "$tool" == "aider" ]]; then
        tmux new-session -d -s "$name" -c "$dir"

        if command -v nvim &> /dev/null; then
          tmux send-keys -t "$name" "nvim" Enter
        fi

        if command -v aider &> /dev/null; then
          tmux split-window -h -t "$name" -c "$dir"
          tmux send-keys -t "$name" "with_secrets aider" Enter
        fi
      else
        tmux new-session -d -s "$name" -c "$dir"
        tmux send-keys -t "$name" "opencode" Enter
        tmux new-window -t "$name" -c "$dir"
        tmux split-window -h -t "$name:1" -c "$dir"
        tmux send-keys -t "$name:1.0" "nvim" Enter
        tmux select-window -t "$name:0"
      fi

      if [ "$attach" = true ]; then
        if [ -n "$TMUX" ]; then
          tmux switch-client -t "$name"
        else
          tmux attach -t "$name"
        fi
      fi
    fi
  }
else
  function dev() {
    echo "Error: tmux is not installed."
  }
fi

# llm commit messages
function gsuggest() {
  if ! command -v llm &>/dev/null; then
    echo "llm not installed"
    return 1
  fi

  local long_mode=0
  if [[ "$1" == "-l" ]]; then
    long_mode=1
  fi

  local diff
  diff=$(git diff --staged)
  [[ -z "$diff" ]] && diff=$(git diff HEAD)

  if [[ -z "$diff" ]]; then
    echo "Nothing to commit"
    return 1
  fi

  local prompt
  if (( long_mode )); then
    prompt="Output a git commit message. Conventional commits: lowercase type(scope?): subject. Add a body (2-4 sentences) explaining what changed and why. No headers, no commentary outside the message. Multiple unrelated changes: number each message."
  else
    prompt="Output only a git commit message title. No body, no prose, no commentary. Conventional commits: lowercase type(scope?): subject. Max 72 chars. Multiple unrelated changes: number each title."
  fi
  
  # Ensure secrets are loaded and use the robust clipboard helper
  with_secrets llm -s "$prompt" "$diff" | tee /dev/tty | _copy
}

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
export PATH="$HOME/.opencode/bin:$PATH"

# PIP, disallow installing without virtualenv
export PIP_REQUIRE_VIRTUALENV=true
