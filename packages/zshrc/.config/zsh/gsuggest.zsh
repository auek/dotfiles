# Clipboard helper for suggested commit messages.
_copy() {
  if command -v clip.exe >/dev/null 2>&1; then
    clip.exe
  elif command -v wl-copy >/dev/null 2>&1; then
    wl-copy
  elif command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard
  else
    # Drain the pipe, but do not report a successful copy when nothing was saved.
    cat > /dev/null
    print -u2 -r -- 'gsuggest: no clipboard tool found (clip.exe, wl-copy, or xclip); message was not copied.'
    return 1
  fi
}

# LLM commit messages
gsuggest() {
  if ! command -v llm >/dev/null 2>&1; then
    echo "llm not installed"
    return 1
  fi

  local long_mode=0
  local accept_mode=0
  while [[ "$1" == -* ]]; do
    case "$1" in
      -l) long_mode=1 ;;
      -a) accept_mode=1 ;;
      *) echo "gsuggest: unknown flag $1"; return 1 ;;
    esac
    shift
  done

  local diff
  local has_staged=0
  diff=$(git diff --staged)
  if [[ -n "$diff" ]]; then
    has_staged=1
  else
    diff=$(git diff HEAD)
  fi

  if [[ -z "$diff" ]]; then
    echo "Nothing to commit"
    return 1
  fi

  local recent_subjects payload
  recent_subjects=$(git log --format=%s -n 5 2>/dev/null)

  local prompt
  if (( long_mode )); then
    prompt="You write git commit messages.

Produce a conventional commit message:
- first line: type(scope?): subject
- blank line
- body: 3-5 sentences

Rules:
- lowercase unless a proper noun requires otherwise
- no quotes, code fences, bullets, numbering, or commentary
- use the example commit subjects only as style reference, never as content
- base the result on the diff
- the body should explain what changed and why, not just restate the diff
- paragraph breaks are allowed when they improve readability
- prefer a concrete, specific summary over a generic one
- if the diff is mixed, summarize the dominant change"
  else
    prompt="You write git commit messages.

Produce only a commit title in the format type(scope?): subject.
Rules:
- lowercase unless a proper noun requires otherwise
- max 72 characters
- no quotes, code fences, bullets, numbering, or commentary
- use the example commit subjects only as style reference, never as content
- base the result on the diff
- prefer a concrete, specific summary over a generic one
- if the diff is mixed, summarize the dominant change"
  fi

  payload="Current diff:
$diff"

  if [[ -n "$recent_subjects" ]]; then
    payload="Example recent commit subjects for style reference only:
$recent_subjects

$payload"
  fi
  if (( accept_mode )); then
    if (( has_staged )); then
      llm -s "$prompt" "$payload" | tee /dev/tty | git commit -F -
    else
      llm -s "$prompt" "$payload" | tee /dev/tty | git commit -a -F -
    fi
  else
    llm -s "$prompt" "$payload" | tee /dev/tty | _copy
  fi
}
