HISTFILE="$HOME/.bash_history"
HISTSIZE=500000
HISTFILESIZE=500000

shopt -s histappend

if [[ $- == *i* ]]; then
    bind 'set bell-style none'
    bind 'set completion-ignore-case on'
fi

# colored prompt
if [ "$TERM" != "dumb" ] && [ -x /usr/bin/tput ] && tput setaf 1 >/dev/null 2>&1; then
    PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
fi

alias p='pwd'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../../..'

alias gst='git status --short'
alias gb='git branch --sort=-committerdate'
alias glg='git log'
alias gl='git pull'
alias gco='git checkout'
alias gcm="git checkout main || git checkout master"
alias gc-="git checkout -"

# tmx: list, attach to, or create a session with optional local customization.
tmx() {
    if [[ "$#" -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
        printf '%s\n' 'Usage: tmx [<session_name> [<directory>]]'
        printf '%s\n' 'Without arguments, list sessions. New sessions default to the current directory.'
        printf '%s\n' 'New-session hook: ${XDG_CONFIG_HOME:-$HOME/.config}/tmx/init.bash'
        return 0
    fi
    if [[ "$#" -gt 2 || ( "$#" -gt 0 && ( -z "$1" || "$1" == -* || "$1" == *[.:]* || "$1" == '$'* ) ) ]]; then
        printf '%s\n' "tmx: invalid arguments; names cannot contain '.' or ':' or start with '-' or '$'. See tmx -h" >&2
        return 1
    fi
    if ! command -v tmux >/dev/null 2>&1; then
        printf '%s\n' 'tmx: tmux is not installed.' >&2
        return 1
    fi

    if [[ "$#" -eq 0 ]]; then
        local listing
        if listing=$(command tmux list-sessions 2>&1); then
            printf '%s\n' "$listing"
        elif [[ "$listing" == *"no server running"* || "$listing" == *"no sessions"* || "$listing" == *"No such file or directory"* ]]; then
            printf '%s\n' 'No tmux sessions. Create one with: tmx <name> [<directory>]'
        else
            printf '%s\n' "$listing" >&2
            return 1
        fi
        return 0
    fi

    local name=$1 target="=$1"
    if ! command tmux has-session -t "$target" 2>/dev/null; then
        local dir=${2-$PWD}
        if [[ ! -d "$dir" ]]; then
            printf 'tmx: directory does not exist: %s\n' "$dir" >&2
            return 1
        fi
        [[ "$dir" == /* ]] || dir=$PWD/$dir
        dir=$(cd -- "$dir" >/dev/null && pwd -P) || return

        local width=$COLUMNS height=$LINES
        if [[ -n "$TMUX" ]]; then
            local dimensions
            dimensions=$(command tmux display-message -p '#{window_width} #{window_height}') || return
            read -r width height <<< "$dimensions"
        fi
        # Create detached so the hook finishes before attachment. Some terminals
        # briefly report zero dimensions while initializing.
        if [[ ! "$width" =~ ^[1-9][0-9]*$ ]]; then
            width=$(tput cols 2>/dev/null)
            [[ "$width" =~ ^[1-9][0-9]*$ ]] || width=220
        fi
        if [[ ! "$height" =~ ^[1-9][0-9]*$ ]]; then
            height=$(tput lines 2>/dev/null)
            [[ "$height" =~ ^[1-9][0-9]*$ ]] || height=50
        fi

        local created session window pane
        created=$(command tmux new-session -d -s "$name" -c "$dir" \
            -x "$width" -y "$height" -P -F '#{session_id} #{window_id} #{pane_id}') || return
        read -r session window pane <<< "$created"
        target=$session

        # Run only trusted machine-local code, never a file from the project.
        # A separate Bash keeps hook variables/options/cd out of this shell.
        local config_home=${XDG_CONFIG_HOME:-$HOME/.config}
        [[ "$config_home" == /* ]] || config_home=$HOME/.config
        local hook=$config_home/tmx/init.bash
        if [[ -e "$hook" ]]; then
            if [[ ! -f "$hook" || ! -r "$hook" ]] || \
                ! command bash --noprofile --norc -ef -- "$hook" "$session" "$window" "$pane" "$dir"; then
                printf "tmx: hook failed: %s; session '%s' remains available (reattachment will not retry the hook).\n" "$hook" "$name" >&2
            fi
        fi
    fi

    if [[ -n "$TMUX" ]]; then
        command tmux switch-client -t "$target"
    else
        command tmux attach-session -t "$target"
    fi
}

# Machine-local overrides; keep this file outside the repository.
if [[ -f "$HOME/.bashrc.private" ]]; then
    source "$HOME/.bashrc.private"
fi
