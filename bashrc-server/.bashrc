HISTFILE="$HOME/.bash_history"
HISTSIZE=500000
HISTFILESIZE=500000

shopt -s histappend

bind 'set bell-style none'
bind 'set completion-ignore-case on'

# colored prompt
if [ "$TERM" != "dumb" ] && [ -x /usr/bin/tput ] && tput setaf 1 >/dev/null 2>&1; then
    PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
fi

alias p='pwd'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../../..'

alias gst='git status'
alias gb='git branch'
alias glg='git log'
alias gl='git pull'
alias gcm="git checkout main || git checkout master"
alias gc-="git checkout -"

# tmx: attach to or create a minimal tmux session.
tmx() {
    if ! command -v tmux >/dev/null 2>&1; then
        echo "Error: tmux is not installed."
        return 127
    fi

    if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
        echo "Usage: tmx <session_name> [<directory>]"
        return 1
    fi

    local name=$1
    local dir=${2:-$PWD}

    if [ ! -d "$dir" ]; then
        echo "Error: directory does not exist: $dir"
        return 1
    fi

    if [ -n "$TMUX" ]; then
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
