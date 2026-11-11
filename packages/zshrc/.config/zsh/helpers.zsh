# Refuse npm in projects declaring another manager; `command npm` bypasses this.
npm() {
  local manager
  # Node is already npm's runtime; read JSON without loading project code.
  # Workspace manifests inherit from parents, up to and including the Git root.
  manager=$(command node -e '
    const fs = require("node:fs");
    const path = require("node:path");
    let dir = process.cwd();
    for (;;) {
      try {
        const pkg = JSON.parse(fs.readFileSync(path.join(dir, "package.json"), "utf8"));
        if (typeof pkg.packageManager === "string" && pkg.packageManager) {
          process.stdout.write(pkg.packageManager);
          break;
        }
      } catch {}
      // Both repository directories and worktree/submodule .git files bound the search.
      if (fs.existsSync(path.join(dir, ".git"))) break;
      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  ' 2>/dev/null)
  case "$manager" in
    pnpm|pnpm@*|yarn|yarn@*|bun|bun@*)
      print -u2 -r -- "npm: this project declares packageManager '$manager'; use ${manager%%@*} instead (or command npm to bypass)."
      return 1
      ;;
  esac
  command npm "$@"
}

# ddcutil brightness helpers: no arguments reads current/max brightness.
if command -v ddcutil >/dev/null 2>&1; then
  br() {
    if (( $# == 0 )); then
      local result=0
      print -r -- "Display 1:"
      br1 || result=1
      print -r -- "Display 2:"
      br2 || result=1
      return "$result"
    fi
    ( ddcutil --display 1 setvcp 10 "$1" >/dev/null & ddcutil --display 2 setvcp 10 "$1" >/dev/null & wait )
  }
  br1() {
    if (( $# == 0 )); then
      ddcutil --display 1 getvcp 10
    else
      ddcutil --display 1 setvcp 10 "$1"
    fi
  }
  br2() {
    if (( $# == 0 )); then
      ddcutil --display 2 getvcp 10
    else
      ddcutil --display 2 setvcp 10 "$1"
    fi
  }
fi

# Cross-platform open command
open() {
  if [[ "$(uname)" == "Darwin" ]]; then
    command open "${@:-.}"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    explorer.exe "${@:-.}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${@:-.}"
  else
    echo "open: no handler found for this platform" >&2
    return 1
  fi
}
