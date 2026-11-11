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
