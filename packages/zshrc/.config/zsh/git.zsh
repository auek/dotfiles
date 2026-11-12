alias gst="git status --short --branch"
alias gb="git branch --sort=-committerdate"
alias glg="git log"
alias gp="git push"
alias gpsup="git push -u origin HEAD"
alias gl="git pull"
alias gcane="git commit --amend --no-edit"
alias gcam="git commit -am"
alias gcmsg="git commit -m"
alias gco="git checkout"
alias gc-="git checkout -"

# Start a new branch from origin's cached trunk, without tracking the trunk.
unalias gcb 2>/dev/null || true
gcb() {
  if (( $# != 1 )) || [[ -z "$1" || "$1" == -* ]]; then
    print -u2 -r -- 'Usage: gcb <branch-name>'
    return 1
  fi
  local branch=$1 trunk candidate
  command git check-ref-format --branch "$branch" >/dev/null || return
  [[ "$branch" != '@{'* ]] || return 1
  trunk=$(command git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || trunk=
  if [[ "$trunk" != origin/main && "$trunk" != origin/master ]] ||
      ! command git show-ref --verify --quiet "refs/remotes/$trunk"; then
    trunk=
    for candidate in main master; do
      if command git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
        if [[ -n "$trunk" ]]; then
          print -u2 -r -- 'gcb: both main and master exist; refresh the default with git remote set-head origin --auto.'
          return 1
        fi
        trunk="origin/$candidate"
      fi
    done
  fi
  if [[ -z "$trunk" ]]; then
    print -u2 -r -- 'gcb: no fetched origin/main or origin/master; run git fetch origin first.'
    return 1
  fi
  command git switch --no-track -c "$branch" "$trunk"
}

# Remove the old alias too when re-sourcing an existing shell.
unalias gcm 2>/dev/null || true
gcm() {
  local trunk candidate
  command git rev-parse --git-dir >/dev/null || return
  trunk=$(command git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || trunk=
  if [[ "$trunk" == origin/main || "$trunk" == origin/master ]] &&
      command git show-ref --verify --quiet "refs/remotes/$trunk"; then
    trunk=${trunk#origin/}
  else
    trunk=
    for candidate in main master; do
      if command git show-ref --verify --quiet "refs/heads/$candidate" ||
          command git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
        if [[ -n "$trunk" ]]; then
          print -u2 -r -- 'gcm: both main and master exist; set origin/HEAD or check out the intended branch explicitly.'
          return 1
        fi
        trunk=$candidate
      fi
    done
  fi
  if [[ -z "$trunk" ]]; then
    print -u2 -r -- 'gcm: no main or master branch found locally or on origin.'
    return 1
  fi
  # Resolve first, then attempt one checkout; a conflict must not select another branch.
  if command git show-ref --verify --quiet "refs/heads/$trunk"; then
    command git checkout "$trunk" "$@"
  else
    command git checkout --track -b "$trunk" "origin/$trunk" "$@"
  fi
}

# Merge origin's freshly fetched default branch, whether named main or master.
gmm() {
  local trunk
  command git fetch origin || return
  command git remote set-head origin --auto || return
  trunk=$(command git symbolic-ref --quiet --short refs/remotes/origin/HEAD) || return
  case "$trunk" in
    origin/main|origin/master) command git merge "$trunk" ;;
    *)
      print -u2 -- "gmm: origin's default branch is '$trunk'; expected main or master."
      return 1
      ;;
  esac
}

# Edit a local branch description without changing its name.
gbdesc() {
  command git branch --edit-description "$@"
}

# Branch picking needs fzf, not fd (which is used by the file/directory widgets).
if command -v fzf >/dev/null 2>&1; then
  gbf() {
    local delim=$'\t'
    local branch commit_date description

    branch=$(git for-each-ref refs/heads \
      --sort=-committerdate \
      --format='%(refname:lstrip=2)	%(committerdate:relative)' |
      while IFS="$delim" read -r branch commit_date; do
        description=$(command git config --get "branch.$branch.description" 2>/dev/null) || description=
        # Descriptions may be multiline; keep each picker entry on one row.
        description=${description%%$'\n'*}
        description=${description//$'\t'/ }
        description=${description//$'\r'/ }
        printf '%s\t%s\t%s\n' "$branch" "$commit_date" "$description"
      done |
      fzf \
      --with-nth=1,2,3 \
      --delimiter="$delim" \
      --preview '
        branch={1}
        description=$(git config --get "branch.$branch.description" 2>/dev/null) || description=
        printf "DESCRIPTION\n%s\n\nRECENT COMMITS\n" "${description:-No branch description}"
        git --no-pager log -5 --format="%h  %s" "refs/heads/$branch" --
      ' \
      --preview-window='right:60%:wrap' |
      cut -f1) || return

    [[ -n "$branch" ]] || return
    git switch "$branch"
  }
fi
