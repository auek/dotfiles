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

export ZSH="$HOME/.oh-my-zsh"
source $ZSH/oh-my-zsh.sh

### Binds ###
bindkey "[D" backward-word
bindkey "[C" forward-word
bindkey "^[a" beginning-of-line
bindkey "^[e" end-of-line
bindkey "\e\e[D" backward-word
bindkey "\e\e[C" forward-word

### Functions ###
with_secrets() {
  local secrets_file=~/.secrets/secrets_general

  if [ "$1" = "--opencode" ]; then
    secrets_file=~/.secrets/secrets_opencode
    shift
  fi

  if [ -f "$secrets_file" ]; then
    (
      source "$secrets_file"
      "$@"
    )
  else
    echo "Error: $secrets_file file not found."
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

# dev: opencode + nvim + terminal
if command -v tmux &> /dev/null; then
  function dev() {
    local attach=true
    local use_claude=false

    while [[ "$1" == "-d" || "$1" == "-h" || "$1" == "--claude" ]]; do
      if [[ "$1" == "-d" ]]; then
        attach=false
      elif [[ "$1" == "--claude" ]]; then
        use_claude=true
      elif [[ "$1" == "-h" ]]; then
        echo "Usage: dev [-d] [--claude] [-h] <session_name> [<project_path>]"
        echo "  -d             Start session detached (do not attach)"
        echo "  --claude       Use claude as the REPL instead of opencode"
        echo "  -h             Show this help message"
        return 0
      fi
      shift
    done

    if [[ "$#" -lt 1 ]]; then
      echo "Usage: dev [-d] [--claude] [-h] <session_name> [<project_path>]"
      echo "  -d             Start session detached (do not attach)"
      echo "  --claude       Use claude as the REPL instead of opencode"
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
        echo "Usage: dev [-d] [--claude] [-h] <session_name> [<project_path>]"
        return 1
      fi
      tmux new-session -d -s "$name" -c "$dir"
      if [[ "$use_claude" == true ]]; then
        tmux send-keys -t "$name" "claude" Enter
      else
        tmux send-keys -t "$name" "with_secrets --opencode opencode" Enter
      fi
      tmux new-window -t "$name" -c "$dir"
      tmux split-window -h -t "$name:1" -c "$dir"
      tmux send-keys -t "$name:1.0" "nvim" Enter
      tmux select-window -t "$name:0"

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

  local recent_subjects payload
  recent_subjects=$(git log --format=%s -n 5 2>/dev/null)

  local prompt
  if (( long_mode )); then
    prompt="You write git commit messages.

Produce a conventional commit message:
- first line: type(scope?): subject
- blank line
- body: 3-5 sentences

Rules:
- lowercase unless a proper noun requires otherwise
- no quotes, code fences, bullets, numbering, or commentary
- use the example commit subjects only as style reference, never as content
- base the result on the diff
- the body should explain what changed and why, not just restate the diff
- paragraph breaks are allowed when they improve readability
- prefer a concrete, specific summary over a generic one
- if the diff is mixed, summarize the dominant change"
  else
    prompt="You write git commit messages.

Produce only a commit title in the format type(scope?): subject.
Rules:
- lowercase unless a proper noun requires otherwise
- max 72 characters
- no quotes, code fences, bullets, numbering, or commentary
- use the example commit subjects only as style reference, never as content
- base the result on the diff
- prefer a concrete, specific summary over a generic one
- if the diff is mixed, summarize the dominant change"
  fi

  payload="Current diff:
$diff"

  if [[ -n "$recent_subjects" ]]; then
    payload="Example recent commit subjects for style reference only:
$recent_subjects

$payload"
  fi
  
  # Ensure secrets are loaded and use the robust clipboard helper
  with_secrets llm -s "$prompt" "$payload" | tee /dev/tty | _copy
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
alias llm='with_secrets llm'
alias opencode='with_secrets --opencode opencode'

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

  gbfz() {
    local delim=$'\t'
    local branch

    branch=$(git for-each-ref refs/heads \
      --sort=-committerdate \
      --format='%(refname:short)	%(committerdate:relative)' |
      fzf \
      --with-nth=1,2 \
      --delimiter="$delim" \
      --preview 'git log -1 --format="%s%n%n%b" {1}' \
      --preview-window='right:60%:wrap' |
      cut -f1) || return

    [[ -n "$branch" ]] || return
    git switch "$branch"
  }

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
