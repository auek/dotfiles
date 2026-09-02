#!/usr/bin/env zsh

### Environment ###
HISTFILE=~/.zsh_history
HISTSIZE=500000
SAVEHIST=500000

export PATH="$HOME/.opencode/bin:$PATH"
export PIP_REQUIRE_VIRTUALENV=true
export ZSH="$HOME/.oh-my-zsh"

# NVM
export NVM_DIR="$HOME/.nvm"
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
[[ -s "$NVM_DIR/bash_completion" ]] && source "$NVM_DIR/bash_completion"

### Shell Behavior ###
setopt append_history
setopt inc_append_history
setopt share_history
unsetopt beep
unsetopt auto_cd

### Completion ###
# Case-insensitive completion.
zstyle ":completion:*" matcher-list "m:{a-z}={A-Za-z}"
autoload -Uz compinit && compinit

### Oh My Zsh Configuration ###
ZSH_THEME="robbyrussell"
plugins=(git ssh-agent zsh-autosuggestions)

# OMZ Plugin Settings
zstyle ':omz:*' aliases no
zstyle :omz:plugins:ssh-agent identities id_ed25519

source "$ZSH/oh-my-zsh.sh"

### Binds ###
# Oh My Zsh maps Alt+L to execute `ls`; retain the standard Emacs-style action.
bindkey '\el' down-case-word
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

  if [[ -f "$secrets_file" ]]; then
    (
      source "$secrets_file"
      "$@"
    )
  else
    echo "Error: $secrets_file file not found."
    return 1
  fi
}

# ddcutil brightness helpers
if command -v ddcutil >/dev/null 2>&1; then
  br()  { ( ddcutil --display 1 setvcp 10 "$1" >/dev/null & ddcutil --display 2 setvcp 10 "$1" >/dev/null & wait ); }
  br1() { ddcutil --display 1 setvcp 10 "$1"; }
  br2() { ddcutil --display 2 setvcp 10 "$1"; }
fi

# Hyprland IPC helper for terminals missing HYPRLAND_INSTANCE_SIGNATURE.
hctl() {
  if ! command -v Hyprland >/dev/null 2>&1; then
    echo "hctl: Hyprland is not installed" >&2
    return 127
  fi

  if ! command -v hyprctl >/dev/null 2>&1; then
    echo "hctl: hyprctl is not installed" >&2
    return 127
  fi

  if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
    command hyprctl "$@"
    return
  fi

  local -a instances
  instances=("${(@f)$(command hyprctl instances 2>/dev/null | awk '/^instance / {sub(/^instance /, ""); sub(/:$/, ""); print}')}")

  if (( ${#instances[@]} == 0 )); then
    echo "hctl: no running Hyprland instance found" >&2
    return 1
  fi

  if (( ${#instances[@]} > 1 )); then
    echo "hctl: multiple Hyprland instances found; select one with hyprctl -i" >&2
    command hyprctl instances >&2
    return 1
  fi

  command hyprctl -i "$instances[1]" "$@"
}

# Cross-platform open command
open() {
  if [[ "$(uname)" == "Darwin" ]]; then
    command open "${@:-.}"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    explorer.exe "${@:-.}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${@:-.}"
  else
    echo "open: no handler found for this platform" >&2
    return 1
  fi
}

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
if command -v tmux >/dev/null 2>&1; then
  # tmx: attach to or create a minimal tmux session.
  tmx() {
    if [[ "$#" -lt 1 || "$#" -gt 2 ]]; then
      echo "Usage: tmx <session_name> [<directory>]"
      return 1
    fi

    local name=$1
    local dir=${2:-$PWD}

    if [[ ! -d "$dir" ]]; then
      echo "Error: directory does not exist: $dir"
      return 1
    fi

    if [[ -n "$TMUX" ]]; then
      if tmux has-session -t "=$name" 2>/dev/null; then
        tmux switch-client -t "=$name"
      else
        tmux new-session -d -s "$name" -c "$dir" && \
          tmux switch-client -t "=$name"
      fi
    else
      tmux new-session -A -s "$name" -c "$dir"
    fi
  }

  dev() {
    local attach=true

    while [[ "$1" == "-d" || "$1" == "-h" ]]; do
      if [[ "$1" == "-d" ]]; then
        attach=false
      elif [[ "$1" == "-h" ]]; then
        echo "Usage: dev [-d] [-h] <session_name> [<project_path>]"
        echo "  -d             Start session detached (do not attach)"
        echo "  -h             Show this help message"
        return 0
      fi
      shift
    done

    if [[ "$#" -lt 1 ]]; then
      echo "Usage: dev [-d] [-h] <session_name> [<project_path>]"
      echo "  -d             Start session detached (do not attach)"
      echo "  -h             Show this help message"
      return 1
    fi

    local name=$1
    local dir=$2

    if tmux has-session -t "$name" 2>/dev/null; then
      if [ "$attach" = true ]; then
        if [[ -n "$TMUX" ]]; then
          tmux switch-client -t "$name"
        else
          tmux attach -t "$name"
        fi
      fi
    else
      if [[ -z "$dir" ]]; then
        echo "Error: project path required to create a new session"
        echo "Usage: dev [-d] [-h] <session_name> [<project_path>]"
        return 1
      fi

      if [[ ! -d "$dir" ]]; then
        echo "Error: directory does not exist: $dir"
        return 1
      fi

      local current_width current_height
      if [[ -n "$TMUX" ]]; then
        current_width=$(tmux display -p '#{window_width}')
        current_height=$(tmux display -p '#{window_height}')
      else
        current_width=${COLUMNS:-$(tput cols 2>/dev/null || echo 220)}
        current_height=${LINES:-$(tput lines 2>/dev/null || echo 50)}

        # Foot can briefly report zero dimensions while its Wayland surface is
        # initializing; tmux rejects those values when creating a detached session.
        if [[ ! "$current_width" =~ '^[1-9][0-9]*$' ]]; then
          current_width=$(tput cols 2>/dev/null)
          [[ "$current_width" =~ '^[1-9][0-9]*$' ]] || current_width=220
        fi
        if [[ ! "$current_height" =~ '^[1-9][0-9]*$' ]]; then
          current_height=$(tput lines 2>/dev/null)
          [[ "$current_height" =~ '^[1-9][0-9]*$' ]] || current_height=50
        fi
      fi
      tmux new-session -d -s "$name" \
        -x "$current_width" -y "$current_height" \
        -c "$dir"
      tmux send-keys -t "$name" "opencode" Enter
      tmux split-window -h -p 30 -t "$name" -c "$dir"
      tmux select-pane -t "$name:0.0"

      if [ "$attach" = true ]; then
        if [[ -n "$TMUX" ]]; then
          tmux switch-client -t "$name"
        else
          tmux attach -t "$name"
        fi
      fi
    fi
  }
else
  dev() {
    echo "Error: tmux is not installed."
  }
fi

# LLM commit messages
gsuggest() {
  if ! command -v llm >/dev/null 2>&1; then
    echo "llm not installed"
    return 1
  fi

  local long_mode=0
  local accept_mode=0
  while [[ "$1" == -* ]]; do
    case "$1" in
      -l) long_mode=1 ;;
      -a) accept_mode=1 ;;
      *) echo "gsuggest: unknown flag $1"; return 1 ;;
    esac
    shift
  done

  local diff
  local has_staged=0
  diff=$(git diff --staged)
  if [[ -n "$diff" ]]; then
    has_staged=1
  else
    diff=$(git diff HEAD)
  fi

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
  if (( accept_mode )); then
    if (( has_staged )); then
      with_secrets llm -s "$prompt" "$payload" | tee /dev/tty | git commit -F -
    else
      with_secrets llm -s "$prompt" "$payload" | tee /dev/tty | git commit -a -F -
    fi
  else
    with_secrets llm -s "$prompt" "$payload" | tee /dev/tty | _copy
  fi
}

### Aliases ###
# General
alias p="pwd"
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../../.."

# Tool-specific
if command -v eza >/dev/null 2>&1; then
  alias l="eza"
  alias ll="eza -lah --git"
  alias t="eza --all -I .git --icons --sort=type -T -L 2"
  alias tt="eza --all -I .git --icons --sort=type -T"
fi

if command -v nvim >/dev/null 2>&1; then
  alias vim="nvim"
fi

# Git
alias gst="git status --short"
alias gb="git branch --sort=-committerdate"
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

# SSH
if [[ -z "$SSH_AUTH_SOCK" ]]; then
  eval "$(ssh-agent -s)" > /dev/null
  ssh-add 2>/dev/null
fi

### External Tool Integrations ###
# FZF configuration (only if fd is available).
if command -v fd >/dev/null 2>&1; then
  FZF_CMD_ARGS="--hidden --exclude .git --exclude node_modules --exclude .cache --exclude .venv --exclude cache"

  export FZF_DEFAULT_COMMAND="fd --type f $FZF_CMD_ARGS"
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND="fd --type d $FZF_CMD_ARGS"

  gbf() {
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
    local dir
    dir=$(fd --type d --max-depth 5 ${=FZF_CMD_ARGS} . "$HOME" 2>/dev/null | fzf)
    if [[ -n "$dir" ]]; then
      cd "$dir"
      zle reset-prompt
    fi
  }
  zle -N fzf-cd-home
  bindkey "\eC" fzf-cd-home

  # Check for bat to provide rich previews, otherwise fallback
  if command -v bat >/dev/null 2>&1; then
    export FZF_DEFAULT_OPTS='--tmux center --preview "[[ -f {} ]] && bat --color=always --style=header,grid --line-range :500 {} || echo {} is a directory"'
  else
    export FZF_DEFAULT_OPTS='--tmux center --preview "[[ -f {} ]] && head -n 500 {} || echo {} is a directory"'
  fi

  source <(fzf --zsh)
fi
