alias gst="git status --short --branch"
alias glg="git log"
alias gp="git push"
alias gpsup="git push -u origin HEAD"
alias gl="git pull"
alias gcane="git commit --amend --no-edit"
alias gcam="git commit -am"
alias gcmsg="git commit -m"
alias gco="git checkout"
alias gc-="git checkout -"

# Only bare gb adds descriptions; arguments keep the normal git branch interface.
unalias gb 2>/dev/null || true
gb() {
  emulate -L zsh
  if (( $# )); then
    command git branch --sort=-committerdate "$@"
    return
  fi
  local listing line branch description color=never tty=false
  local -a rows colored
  local -i width=0 index
  listing=$(command git branch --sort=-committerdate --no-column --no-color) || return
  [[ -n "$listing" ]] || return 0
  rows=("${(@f)listing}")
  # Resolve auto colors against our output, rather than the command substitution.
  [[ -t 1 ]] && tty=true
  if [[ $(command git config --get-colorbool color.branch "$tty") == true ]]; then
    color=always
  fi
  listing=$(command git branch --sort=-committerdate --no-column --color="$color") || return
  colored=("${(@f)listing}")
  for line in "${rows[@]}"; do
    (( ${(m)#line} > width )) && width=${(m)#line}
  done
  for (( index=1; index<=${#rows}; index++ )); do
    line=${rows[index]}
    branch=${line[3,-1]}
    description=$(command git config --get "branch.$branch.description" 2>/dev/null) || description=
    # Keep descriptions on one row, without changing the saved multiline text.
    description=${description%%$'\n'*}
    description=${description//$'\t'/ }
    description=${description//$'\r'/ }
    if [[ -n "$description" ]]; then
      printf '%s%*s%s\n' "${colored[index]}" "$(( width - ${(m)#line} + 2 ))" '' "$description"
    else
      print -r -- "${colored[index]}"
    fi
  done
}

if (( $+functions[compdef] )); then
  compdef _git gb=git-branch
fi

# Start a new branch from origin's cached trunk, without tracking the trunk.
unalias gcb 2>/dev/null || true
gcb() {
  if (( $# < 1 || $# > 2 )) || [[ -z "$1" || "$1" == -* ]]; then
    print -u2 -r -- 'Usage: gcb <branch-name> [description]'
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
  command git switch --no-track -c "$branch" "$trunk" || return
  if (( $# == 2 )); then
    if ! command git config --local "branch.$branch.description" "$2"; then
      print -u2 -r -- "gcb: created '$branch', but could not save its description; use gbdesc to retry."
      return 1
    fi
  fi
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

# Jira IDs identify review candidates, never proof that a branch was merged.
_gbclean_interactive() {
  emulate -L zsh
  local trunk=$1 trunk_oid refs branch oid checked_out ticket
  local pattern='(^|[^[:alnum:]])(JIRA-[0-9]+)($|[^[:alnum:]])'
  local history line matches description reply confirmation current_oid
  local -i stop=0
  local -a match mbegin mend selected=()
  local -A groups tips
  trunk_oid=$(command git rev-parse --verify "refs/remotes/$trunk^{commit}") || return
  refs=$(command git for-each-ref refs/heads --sort=refname \
    --format='%(refname:lstrip=2)%09%(objectname)%09%(if)%(worktreepath)%(then)checked-out%(end)') || return
  while IFS=$'\t' read -r branch oid checked_out; do
    [[ -n "$branch" && -z "$checked_out" ]] || continue
    case "$branch" in main|master|develop) continue ;; esac
    if [[ ${(U)branch} =~ $pattern ]]; then
      ticket=$match[2]
      groups[$ticket]+="$branch"$'\n'
      tips[$branch]=$oid
    fi
  done <<< "$refs"
  print -r -- "gbclean: Jira review against cached $trunk (no fetch)."
  print -r -- 'Mark branches for deletion, then confirm the full list at the end. Nothing is deleted during review.'
  for ticket in "${(@ok)groups}"; do
    pattern="(^|[^[:alnum:]])$ticket($|[^[:alnum:]])"
    # Git grep also searches bodies; filter subjects to require the ID in the title.
    history=$(command git --no-pager log --no-color --format='%h %s' \
      --regexp-ignore-case --extended-regexp --grep="$pattern" "$trunk_oid" --) || return
    matches=
    for line in "${(@f)history}"; do
      if [[ ${(U)line} =~ $pattern ]]; then
        matches+="$line"$'\n'
      fi
    done
    [[ -n "$matches" ]] || continue
    print -r -- "
$ticket — matching commits on ${trunk}:"
    print -rn -- "$matches"
    for branch in "${(@f)groups[$ticket]}"; do
      [[ -n "$branch" ]] || continue
      oid=$tips[$branch]
      description=$(command git config --get "branch.$branch.description" 2>/dev/null) || description=
      print -r -- "
Branch: $branch
Description: ${description:-N/A}
Recent commits:"
      command git --no-pager log -5 --no-color --format='%h %s' "$oid" -- || return
      print -r -- 'Jira match only; this branch may contain additional work.'
      while true; do
        print -n -r -- '[k]eep / [i]nspect / mark for [d]eletion / [q]uit (default: keep): '
        IFS= read -r reply || { stop=1; break; }
        case "$reply" in
          ''|k|K) break ;;
          q|Q) stop=1; break ;;
          i|I)
            print -r -- "Diff: cached $trunk -> branch tip (includes unrelated trunk differences; not proof of unmerged work)."
            command git --no-pager diff --no-ext-diff --no-textconv "$trunk_oid" "$oid" -- || return
            ;;
          d|D)
            selected+=("$branch")
            print -r -- "Marked for deletion: $branch"
            break
            ;;
          *) print -r -- 'Choose k, i, d, or q.' ;;
        esac
      done
      (( stop )) && break
    done
    (( stop )) && break
  done
  if (( stop )); then
    print -r -- 'Review cancelled; nothing deleted.'
    return 0
  fi
  if (( ${#selected} == 0 )); then
    print -r -- 'No branches selected; nothing deleted.'
    return 0
  fi
  print -r -- '
Selected for deletion:'
  print -rl -- "${selected[@]}"
  print -r -- 'Warning: these branches may contain unmerged work.'
  print -n -r -- "Force-delete ${#selected} local branch(es)? [y/N]: "
  IFS= read -r confirmation || confirmation=
  if [[ "$confirmation" != y && "$confirmation" != Y ]]; then
    print -r -- 'Cancelled; nothing deleted.'
    return 0
  fi
  # Revalidate the entire selection before deleting any branch.
  for branch in "${selected[@]}"; do
    current_oid=$(command git rev-parse --verify "refs/heads/$branch") || return
    if [[ "$current_oid" != "${tips[$branch]}" ]]; then
      print -u2 -r -- "gbclean: '$branch' changed during review; stopped without deleting anything."
      return 1
    fi
    checked_out=$(command git for-each-ref --format='%(worktreepath)' "refs/heads/$branch") || return
    if [[ -n "$checked_out" ]]; then
      print -u2 -r -- "gbclean: '$branch' is now checked out; stopped without deleting anything."
      return 1
    fi
  done
  # Git also checks worktree protections at deletion time.
  command git branch -D -- "${selected[@]}" || return
  print -r -- "Review complete: ${#selected} branch(es) deleted."
  return 0
}

# Preview by default; ordinary deletion retains Git's upstream/HEAD safeguards.
gbclean() {
  emulate -L zsh
  local -i delete=0 interactive=0
  local arg
  for arg in "$@"; do
    case "$arg" in
      --delete) delete=1 ;;
      --interactive) interactive=1 ;;
      -h|--help)
        print -r -- 'Usage: gbclean [--interactive] [--delete]
Preview local branches merged into cached origin/main or origin/master.
Use --delete to remove them with git branch -d; never fetches.
Skips main, master, develop, and branches checked out in any worktree.
Squash merges are not detected by ordinary cleanup. Run git fetch origin first to refresh.
Git may retain candidates not merged into their upstream or current HEAD.
--interactive reviews branches whose JIRA-<number> appears in a trunk commit title.
This is a heuristic, not proof of merging. Keep is the default; i shows a tip diff.
d marks a branch; q or EOF during review cancels everything.
Interactive mode shows the selected list and requires a final y to FORCE-delete it.
No --delete is needed for interactive mode; supplying it never bypasses confirmation.'
        return 0
        ;;
      *) print -u2 -r -- 'Usage: gbclean [--interactive] [--delete]'; return 1 ;;
    esac
  done
  local trunk candidate refs branch checked_out
  local -a branches=()
  command git rev-parse --git-dir >/dev/null || return
  trunk=$(command git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || trunk=
  if [[ "$trunk" != origin/main && "$trunk" != origin/master ]] ||
      ! command git show-ref --verify --quiet "refs/remotes/$trunk"; then
    trunk=
    for candidate in main master; do
      if command git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
        if [[ -n "$trunk" ]]; then
          print -u2 -r -- 'gbclean: both main and master exist; refresh the default with git remote set-head origin --auto.'
          return 1
        fi
        trunk="origin/$candidate"
      fi
    done
  fi
  if [[ -z "$trunk" ]]; then
    print -u2 -r -- 'gbclean: no fetched origin/main or origin/master; run git fetch origin first.'
    return 1
  fi
  if (( interactive )); then
    _gbclean_interactive "$trunk"
    return
  fi
  refs=$(command git for-each-ref refs/heads --merged="refs/remotes/$trunk" \
    --format='%(refname:lstrip=2)%09%(if)%(worktreepath)%(then)checked-out%(end)') || return
  while IFS=$'\t' read -r branch checked_out; do
    [[ -n "$branch" && -z "$checked_out" ]] || continue
    case "$branch" in main|master|develop) continue ;; esac
    branches+=("$branch")
  done <<< "$refs"
  if (( ${#branches} == 0 )); then
    print -r -- "gbclean: no removable branches merged into cached $trunk."
    return 0
  fi
  print -r -- "gbclean: merged into cached $trunk (no fetch):"
  if (( ! delete )); then
    print -rl -- "${branches[@]}"
    print -r -- 'Preview only. Run gbclean --delete to attempt safe deletion.'
    return 0
  fi
  for branch in "${branches[@]}"; do
    if ! command git branch -d -- "$branch"; then
      print -u2 -r -- "gbclean: Git refused '$branch'; stopped without forcing deletion."
      return 1
    fi
  done
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
        printf "DESCRIPTION\n%s\n\nRECENT COMMITS\n" "${description:-N/A}"
        # Clip commit subjects to the pane width while allowing descriptions to wrap.
        git --no-pager log -5 --format="%h  %<|(${FZF_PREVIEW_COLUMNS:-80},trunc)%s" "refs/heads/$branch" --
      ' \
      --preview-window='right:60%:wrap' |
      cut -f1) || return

    [[ -n "$branch" ]] || return
    git switch "$branch"
  }
fi
