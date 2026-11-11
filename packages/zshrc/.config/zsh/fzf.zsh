# FZF configuration (both tools are needed, including during partial installs).
if command -v fd >/dev/null 2>&1 && command -v fzf >/dev/null 2>&1; then
  FZF_CMD_ARGS="--hidden --exclude .git --exclude node_modules --exclude .cache --exclude .venv --exclude cache"

  export FZF_DEFAULT_COMMAND="fd --type f $FZF_CMD_ARGS"
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND="fd --type d $FZF_CMD_ARGS"

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
