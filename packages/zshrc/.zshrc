#!/usr/bin/env zsh

### Environment ###
HISTFILE=~/.zsh_history
HISTSIZE=500000
SAVEHIST=400000

typeset -U path PATH
path=("$HOME/.local/bin" $path)
export PATH
export PIP_REQUIRE_VIRTUALENV=true
export ZSH="$HOME/.oh-my-zsh"

if command -v less >/dev/null 2>&1; then
  export PAGER=less
  export LESS='-QR'
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

# The ssh-agent plugin owns agent startup and identity loading.
zstyle ':omz:*' aliases no
zstyle :omz:plugins:ssh-agent identities id_ed25519

source "$ZSH/oh-my-zsh.sh"

### Binds ###
# Oh My Zsh maps Alt+L to execute `ls`; retain the standard Emacs-style action.
bindkey '\el' down-case-word
# Clear the screen without losing the current input (Ctrl+L navigates tmux panes).
bindkey '\ek' clear-screen
bindkey '\ea' beginning-of-line
bindkey '\ee' end-of-line
bindkey '\e\e[D' backward-word
bindkey '\e\e[C' forward-word

### Everyday Aliases ###
alias p="pwd"
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../../.."

if command -v bat >/dev/null 2>&1; then
  # Use the terminal palette so bat and fzf previews follow theme changes.
  export BAT_THEME=ansi
  alias bat="bat --style=plain"
fi

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

### Feature Modules ###
# Resolve this entrypoint's symlink so existing Stow links work before restowing.
# Modules belong to this package, not the cwd or a machine-local XDG directory.
_dotfiles_zsh_dir=${${(%):-%x}:A:h}/.config/zsh
source "$_dotfiles_zsh_dir/helpers.zsh"
source "$_dotfiles_zsh_dir/tmx.zsh"
source "$_dotfiles_zsh_dir/git.zsh"
source "$_dotfiles_zsh_dir/worktrees.zsh"
source "$_dotfiles_zsh_dir/gsuggest.zsh"
source "$_dotfiles_zsh_dir/fzf.zsh"
unset _dotfiles_zsh_dir

# Machine-local environment overrides; keep this file outside the repository.
if [[ -f "$HOME/.zshrc.private" ]]; then
  source "$HOME/.zshrc.private"
fi
