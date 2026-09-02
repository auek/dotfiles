#!/usr/bin/env bash
# PreToolUse hook (Bash matcher). Auto-allows `git push` only when none of
# the resolved target branches are main/master/develop, so the existing
# "Bash(git push *)" ask rule still gates pushes to those branches (and any
# push whose target branch can't be confidently resolved).
set -euo pipefail

input="$(cat)"
tool="$(jq -r '.tool_name // empty' <<<"$input")"
cmd="$(jq -r '.tool_input.command // empty' <<<"$input")"

[[ "$tool" == "Bash" && -n "$cmd" ]] || exit 0

# Reject anything with shell metacharacters/chaining or embedded newlines -
# only a single, literal `git push ...` invocation is eligible.
if [[ "$cmd" == *[\;\&\|\`\$\<\>]* || "$cmd" == *$'\n'* ]]; then
  exit 0
fi

[[ "$cmd" =~ ^git[[:space:]]+push([[:space:]]|$) ]] || exit 0

# Never auto-allow force pushes or bulk/tag pushes - defer to the ask/deny rules.
if [[ "$cmd" =~ (^|[[:space:]])(-f|--force|--force-with-lease|--force-if-includes|--all|--mirror|--tags)([[:space:]]|$) ]]; then
  exit 0
fi

protected_re='^(main|master|develop)$'

current_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null || true
}

read -r -a tokens <<<"$cmd"
args=()
for ((i = 2; i < ${#tokens[@]}; i++)); do
  tok="${tokens[$i]}"
  [[ "$tok" == -* ]] && continue
  args+=("$tok")
done

branches=()
if [[ ${#args[@]} -le 1 ]]; then
  # bare `git push` or `git push <remote>`: targets the current branch.
  cur="$(current_branch)"
  [[ -n "$cur" ]] || exit 0
  branches+=("$cur")
else
  for ((i = 1; i < ${#args[@]}; i++)); do
    refspec="${args[$i]#+}"
    if [[ "$refspec" == *:* ]]; then
      dst="${refspec#*:}"
    else
      dst="$refspec"
    fi
    dst="${dst#refs/heads/}"
    [[ -n "$dst" ]] || exit 0
    if [[ "$dst" == "HEAD" ]]; then
      dst="$(current_branch)"
      [[ -n "$dst" ]] || exit 0
    fi
    branches+=("$dst")
  done
fi

for b in "${branches[@]}"; do
  if [[ "$b" =~ $protected_re ]]; then
    exit 0
  fi
done

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"push targets a non-protected branch"}}'
