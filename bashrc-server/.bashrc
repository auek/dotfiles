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
