HISTFILE="$HOME/.bash_history"
HISTSIZE=500000
HISTFILESIZE=500000

shopt -s histappend

bind 'set bell-style none'
bind 'set completion-ignore-case on'

alias p='pwd'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../../..'

alias gst='git status'
alias gb='git branch'
alias glg='git log'
