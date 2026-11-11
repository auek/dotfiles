alias gwl="git worktree list"

# Worktree helpers use Git's registry, not a machine-specific repository path.
# Relative dotfiles.worktreeDir values are based on the original checkout:
#   git config --local dotfiles.worktreeDir ../worktrees
# The default (..) puts new worktrees beside the original checkout.
_gwt_load() {
  local listing record base
  listing=$(command git worktree list --porcelain -z) || return
  for record in "${(@0)listing}"; do
    case "$record" in
      'worktree '*)
        gwt_dirs+=("${record#worktree }")
        gwt_branches+=('(detached)')
        ;;
      'branch '*) gwt_branches[-1]=${record#branch refs/heads/} ;;
      bare)
        print -u2 -r -- 'Worktree helpers require a non-bare original checkout.'
        return 1
        ;;
    esac
  done
  gwt_main=${gwt_dirs[1]}
  [[ -n "$gwt_main" ]] || return 1
  if base=$(command git config --get dotfiles.worktreeDir); then
    [[ -n "$base" ]] || { print -u2 -r -- 'dotfiles.worktreeDir must not be empty.'; return 1; }
  else
    (( $? == 1 )) || return
    base=..
  fi
  [[ "$base" == /* ]] || base=$gwt_main/$base
  gwt_parent=${base:A}
}

# Resolve only registered worktrees. Typos must never create a checkout.
_gwt_find() {
  local query=$1 candidate=${1:A}
  local -i i matches=0
  for (( i=1; i<=${#gwt_dirs}; i++ )); do
    if [[ "$query" == "${gwt_dirs[i]:t}" || "$query" == "${gwt_branches[i]}" ||
          "$candidate" == "${gwt_dirs[i]:A}" ]]; then
      gwt_target=${gwt_dirs[i]}
      (( ++matches ))
    fi
  done
  if (( matches != 1 )); then
    print -u2 -r -- "Worktree not found or ambiguous: $query (use an exact path)."
    return 1
  fi
}

gwc() {
  if [[ "$1" == -h || "$1" == --help ]]; then
    print -r -- 'Usage: gwc [<directory-name|branch|path>]'
    print -r -- 'Without arguments, pick a registered worktree with fzf; enter its root.'
    return 0
  fi
  (( $# <= 1 )) || { print -u2 -r -- 'Usage: gwc [<directory-name|branch|path>]'; return 1; }
  local gwt_main gwt_parent gwt_target selection
  local -a gwt_dirs gwt_branches
  _gwt_load || return
  if (( $# )); then
    _gwt_find "$1" || return
  else
    command -v fzf >/dev/null 2>&1 || { print -u2 -r -- 'gwc: fzf is not installed; supply a name or path.'; return 1; }
    selection=$(printf '%s\0' "${gwt_dirs[@]}" |
      command fzf --read0 --print0 --no-multi --no-expect \
        --prompt='Worktree> ' --preview='git -C {} status --short --branch' \
        --preview-window='right:60%:wrap') || return
    # fzf's NUL delimiter preserves spaces, Unicode and newlines in paths.
    gwt_target=${selection%$'\0'}
    [[ -n "$gwt_target" ]] || return 1
    _gwt_find "$gwt_target" || return
  fi
  builtin cd -- "$gwt_target"
}

gwa() {
  local -i no_cd=0
  if [[ "$1" == --no-cd ]]; then
    no_cd=1
    shift
  fi
  if [[ "$1" == -h || "$1" == --help ]]; then
    print -r -- 'Usage: gwa [--no-cd] <directory-name> [<branch>]

Create a worktree and enter it. Branch defaults to directory-name.

Branch selection:
  1. Reuse the local branch, if it exists.
  2. Otherwise, track the matching origin/<branch>, if it exists.
  3. Otherwise, create from origin/main or origin/master with no upstream.

  Prefers cached origin/HEAD when it names an available main or master.
  Otherwise uses the only fetched trunk; refuses ambiguous main/master refs.
  Uses fetched refs. Run git fetch origin first to refresh them.
  Refresh the default-branch hint: git remote set-head origin --auto

Options:
  --no-cd       Create without changing your current directory.
  -h, --help    Show this help.

Examples:
  gwa theme1                  Create and enter theme1.
  gwa theme1 feature/story    Use a different branch name.
  gwa --no-cd theme2          Create theme2 without entering it.

Location:
  Default: beside the original checkout (flat layout).
  To use a worktrees/ directory instead, run once per repository:

    git config --local dotfiles.worktreeDir ../worktrees

  Relative paths resolve from the original checkout, not your current directory.'
    return 0
  fi
  if (( $# < 1 || $# > 2 )) || [[ -z "$1" || "$1" == -* || "$1" == */* || "$1" == . || "$1" == .. ]]; then
    print -u2 -r -- 'Usage: gwa [--no-cd] <directory-name> [<branch>]'
    return 1
  fi
  local name=$1 branch=${2-$1} gwt_main gwt_parent destination
  local -a gwt_dirs gwt_branches
  command git check-ref-format --branch "$branch" >/dev/null || return
  # Do not interpret Git's previous-checkout shorthand as a new branch name.
  [[ "$branch" != '@{'* ]] || return 1
  _gwt_load || return
  destination=$gwt_parent/$name
  if command git show-ref --verify --quiet "refs/heads/$branch"; then
    command git -C "$gwt_main" worktree add -- "$destination" "$branch" || return
  elif command git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    command git -C "$gwt_main" worktree add --track -b "$branch" -- "$destination" "origin/$branch" || return
  else
    local trunk candidate
    trunk=$(command git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || trunk=
    if [[ "$trunk" != origin/main && "$trunk" != origin/master ]] ||
        ! command git show-ref --verify --quiet "refs/remotes/$trunk"; then
      trunk=
      for candidate in main master; do
        if command git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
          if [[ -n "$trunk" ]]; then
            print -u2 -r -- 'gwa: both main and master exist; refresh the default with git remote set-head origin --auto.'
            return 1
          fi
          trunk="origin/$candidate"
        fi
      done
    fi
    if [[ -z "$trunk" ]]; then
      print -u2 -r -- 'gwa: no fetched origin/main or origin/master; run git fetch origin first.'
      return 1
    fi
    command git -C "$gwt_main" worktree add --no-track -b "$branch" -- "$destination" "$trunk" || return
  fi
  if (( ! no_cd )); then
    builtin cd -- "$destination" || return
  fi
  return 0
}

gwm() {
  local -i no_cd=0 inside=0 result
  if [[ "$1" == --no-cd ]]; then
    no_cd=1
    shift
  fi
  if [[ "$1" == -h || "$1" == --help ]]; then
    print -r -- 'Usage: gwm [--no-cd] <directory-name|branch|path> <new-name|path>

Move or rename a linked worktree, keeping its branch and all local files.
A bare new name stays beside the source; paths resolve from the current cwd.
The destination must not exist. Never forces a move or renames the branch.

When inside the source, follow the move and keep the relative subdirectory.
Otherwise, stay in the current directory. --no-cd refuses from inside.
Git cannot move the original checkout or worktrees containing submodules.
Other shells/editors are not relocated; path-dependent caches may need rebuilding.

Examples:
  gwm old-name new-name
  gwm feature/story ../worktrees/story'
    return 0
  fi
  if (( $# != 2 )) || [[ -z "$1" || "$1" == -* || -z "$2" || "$2" == -* || "$2" == . || "$2" == .. ]]; then
    print -u2 -r -- 'Usage: gwm [--no-cd] <directory-name|branch|path> <new-name|path>'
    return 1
  fi
  local gwt_main gwt_parent gwt_target target_real destination=$2
  local old_dir=$PWD current=${PWD:A} suffix
  local -a gwt_dirs gwt_branches
  _gwt_load && _gwt_find "$1" || return
  if [[ "$gwt_target" == "$gwt_main" ]]; then
    print -u2 -r -- 'gwm: refusing to move the original checkout.'
    return 1
  fi
  target_real=${gwt_target:A}
  [[ "$destination" == */* ]] || destination=${gwt_target:h}/$destination
  destination=${destination:a}
  # Git treats an existing directory as a container; require an exact new path.
  if [[ -e "$destination" || -L "$destination" ]]; then
    print -u2 -r -- "gwm: destination already exists: $destination"
    return 1
  fi
  destination=${destination:A}
  if [[ "$destination" == "$target_real/"* ]]; then
    print -u2 -r -- 'gwm: destination cannot be inside the source worktree.'
    return 1
  fi
  if [[ "$current" == "$target_real" || "$current" == "$target_real/"* ]]; then
    if (( no_cd )); then
      print -u2 -r -- 'gwm: leave the source worktree before using --no-cd.'
      return 1
    fi
    suffix=${current#"$target_real"}
    # Run outside the moved tree so neither Git nor this shell retains a stale cwd.
    builtin cd -- "$gwt_main" || return
    inside=1
  fi
  command git -C "$gwt_main" worktree move -- "$gwt_target" "$destination"
  result=$?
  if (( inside )); then
    if (( result )); then
      builtin cd -- "$old_dir" || return
    else
      builtin cd -- "$destination$suffix" || return
    fi
  fi
  return "$result"
}

gwr() {
  local -i no_cd=0 moved=0 result
  if [[ "$1" == --no-cd ]]; then
    no_cd=1
    shift
  fi
  if [[ "$1" == -h || "$1" == --help ]]; then
    print -r -- 'Usage: gwr [--no-cd] <directory-name|branch|path>'
    print -r -- 'Remove a clean linked worktree, keeping its branch. Never forces removal.'
    print -r -- 'When inside the target, move to the original checkout; --no-cd refuses instead.'
    return 0
  fi
  if (( $# != 1 )) || [[ -z "$1" || "$1" == -* ]]; then
    print -u2 -r -- 'Usage: gwr [--no-cd] <directory-name|branch|path>'
    return 1
  fi
  local gwt_main gwt_parent gwt_target target_real old_dir=$PWD current=${PWD:A}
  local -a gwt_dirs gwt_branches
  _gwt_load && _gwt_find "$1" || return
  if [[ "$gwt_target" == "$gwt_main" ]]; then
    print -u2 -r -- 'gwr: refusing to remove the original checkout.'
    return 1
  fi
  target_real=${gwt_target:A}
  if [[ "$current" == "$target_real" || "$current" == "$target_real/"* ]]; then
    if (( no_cd )); then
      print -u2 -r -- 'gwr: leave the target worktree before using --no-cd.'
      return 1
    fi
    builtin cd -- "$gwt_main" || return
    moved=1
  fi
  command git -C "$gwt_main" worktree remove -- "$gwt_target"
  result=$?
  if (( result && moved )); then
    builtin cd -- "$old_dir" || return
  fi
  return "$result"
}

_gwt_complete() {
  local gwt_main gwt_parent
  local -a gwt_dirs gwt_branches
  _gwt_load 2>/dev/null || return
  compadd -- "${gwt_dirs[@]:t}" "${gwt_branches[@]}"
}

_gwm_complete() {
  _arguments \
    '--no-cd[Refuse moving the current worktree]' \
    '1:worktree:_gwt_complete' \
    '2:new name or path:_files -/'
}

if (( $+functions[compdef] )); then
  compdef _gwt_complete gwc gwr
  compdef _gwm_complete gwm
fi
