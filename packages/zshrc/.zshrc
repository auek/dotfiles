#!/usr/bin/env zsh

### Environment ###
HISTFILE=~/.zsh_history
HISTSIZE=500000
SAVEHIST=400000

typeset -U path PATH
path=("$HOME/.local/bin" "$HOME/.opencode/bin" $path)
export PATH
export PIP_REQUIRE_VIRTUALENV=true
export ZSH="$HOME/.oh-my-zsh"

if command -v less >/dev/null 2>&1; then
  export PAGER=less
  export LESS='-R'
fi

# mise (also available in interactive shells that are not login shells).
if command -v mise >/dev/null 2>&1; then
  # Keep shims for subprocesses and commands run before the first prompt.
  path=("${MISE_SHIMS_DIR:-${MISE_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/mise}/shims}" $path)
  eval "$(mise activate zsh)"
fi

### Shell Behavior ###
# Append commands immediately and import history from other shells.
setopt share_history
unsetopt beep
unsetopt auto_cd

### Completion ###
# Case-insensitive completion.
zstyle ":completion:*" matcher-list "m:{a-z}={A-Za-z}"
# Oh My Zsh runs compinit after configuring plugin completion paths.

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
# Retained for occasional commands that need a scoped secrets environment.
# No current aliases or functions depend on it.
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

# tmx: list, attach to, or create a session with optional local customization.
tmx() {
  if [[ "$#" -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    print -r -- "Usage: tmx [<session_name> [<directory>]]"
    print -r -- "Without arguments, list sessions. New sessions default to the current directory."
    print -r -- "New-session hook: \${XDG_CONFIG_HOME:-\$HOME/.config}/tmx/init.zsh"
    return 0
  fi
  if [[ "$#" -gt 2 || ( "$#" -gt 0 && ( -z "$1" || "$1" == -* || "$1" == *[.:]* || "$1" == '$'* ) ) ]]; then
    print -u2 -r -- "tmx: invalid arguments; names cannot contain '.' or ':' or start with '-' or '$'. See tmx -h"
    return 1
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    print -u2 -r -- "tmx: tmux is not installed."
    return 1
  fi

  if [[ "$#" -eq 0 ]]; then
    local listing
    if listing=$(command tmux list-sessions 2>&1); then
      print -r -- "$listing"
    elif [[ "$listing" == *"no server running"* || "$listing" == *"no sessions"* || "$listing" == *"No such file or directory"* ]]; then
      print -r -- "No tmux sessions. Create one with: tmx <name> [<directory>]"
    else
      print -u2 -r -- "$listing"
      return 1
    fi
    return 0
  fi

  local name=$1 target="=$1"
  if ! command tmux has-session -t "$target" 2>/dev/null; then
    local dir=${2-$PWD}
    if [[ ! -d "$dir" ]]; then
      print -u2 -r -- "tmx: directory does not exist: $dir"
      return 1
    fi
    dir=${dir:A}

    local width=$COLUMNS height=$LINES
    if [[ -n "$TMUX" ]]; then
      local dimensions
      dimensions=$(command tmux display-message -p '#{window_width} #{window_height}') || return
      read -r width height <<< "$dimensions"
    fi
    # Detached creation lets the hook finish before attachment. Foot can briefly
    # report zero dimensions while its Wayland surface initializes.
    if [[ ! "$width" =~ '^[1-9][0-9]*$' ]]; then
      width=$(tput cols 2>/dev/null)
      [[ "$width" =~ '^[1-9][0-9]*$' ]] || width=220
    fi
    if [[ ! "$height" =~ '^[1-9][0-9]*$' ]]; then
      height=$(tput lines 2>/dev/null)
      [[ "$height" =~ '^[1-9][0-9]*$' ]] || height=50
    fi

    local created session window pane
    created=$(command tmux new-session -d -s "$name" -c "$dir" \
      -x "$width" -y "$height" -P -F '#{session_id} #{window_id} #{pane_id}') || return
    read -r session window pane <<< "$created"
    target=$session

    # Run only trusted machine-local code, never a file from the project. A
    # separate Zsh keeps hook variables/options/cd out of the interactive shell.
    local config_home=${XDG_CONFIG_HOME:-$HOME/.config}
    # XDG paths must be absolute; a relative value must not load project code.
    [[ "$config_home" == /* ]] || config_home=$HOME/.config
    local hook=$config_home/tmx/init.zsh
    if [[ -e "$hook" ]]; then
      if [[ ! -f "$hook" || ! -r "$hook" ]] || \
          ! command zsh -ef -- "$hook" "$session" "$window" "$pane" "$dir"; then
        print -u2 -r -- "tmx: hook failed: $hook; session '$name' remains available (reattachment will not retry the hook)."
      fi
    fi
  fi

  if [[ -n "$TMUX" ]]; then
    command tmux switch-client -t "$target"
  else
    command tmux attach-session -t "$target"
  fi
}

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
      llm -s "$prompt" "$payload" | tee /dev/tty | git commit -F -
    else
      llm -s "$prompt" "$payload" | tee /dev/tty | git commit -a -F -
    fi
  else
    llm -s "$prompt" "$payload" | tee /dev/tty | _copy
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

if command -v lazygit >/dev/null 2>&1; then
  alias lg="lazygit"
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

# SSH
if [[ -z "$SSH_AUTH_SOCK" ]]; then
  eval "$(ssh-agent -s)" > /dev/null
  ssh-add 2>/dev/null
fi

### External Tool Integrations ###
# FZF configuration (both tools are needed, including during partial installs).
if command -v fd >/dev/null 2>&1 && command -v fzf >/dev/null 2>&1; then
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

# Machine-local environment overrides; keep this file outside the repository.
if [[ -f "$HOME/.zshrc.private" ]]; then
  source "$HOME/.zshrc.private"
fi
