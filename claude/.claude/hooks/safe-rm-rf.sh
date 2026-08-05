#!/usr/bin/env bash
# PreToolUse hook (Bash matcher). Auto-allows `rm -rf` only for exact,
# unchained deletions of known dependency/build/cache directories, so the
# broad "Bash(rm -rf *)" ask rule in settings.json still gates everything else.
set -euo pipefail

input="$(cat)"
tool="$(jq -r '.tool_name // empty' <<<"$input")"
cmd="$(jq -r '.tool_input.command // empty' <<<"$input")"

[[ "$tool" == "Bash" && -n "$cmd" ]] || exit 0

# Reject anything with shell metacharacters/chaining or embedded newlines -
# only a single, literal `rm -rf <path>` invocation is eligible.
if [[ "$cmd" == *[\;\&\|\`\$\<\>]* || "$cmd" == *$'\n'* ]]; then
  exit 0
fi

safe_dirs='node_modules|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|dist|build|\.next|\.nuxt|\.turbo'

if [[ "$cmd" =~ ^rm[[:space:]]+-(rf|fr)[[:space:]]+([./A-Za-z0-9_-]+/)?($safe_dirs)/?$ ]]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"safe dependency/build cache directory"}}'
fi
