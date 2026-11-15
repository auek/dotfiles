# Implementation Plan: Agent tooling on the VPS

Status: not started. Written 2026-11-15 after Playwright MCP landed on the
workstation (`feat/playwright-mcp`). Deferred on purpose: no server work was done.

## Goal

Give Claude Code on the VPS the same capabilities as on the workstation,
starting with Playwright MCP and Context7, and make the VPS reproducible from
this repository so it stops drifting. The VPS is used remotely through
`claude remote-control`, so reliability matters more than polish.

## Findings (as of 2026-11-15)

Host: Ubuntu 24.04, a small VPS (under 4 GB RAM), ample free disk, datacenter IP.

- Dotfiles live in `~/code/dotfiles` on `main`, clean, **72 commits behind**
  `origin/main`. The pending changes touch the server packages themselves
  (`bashrc-server`, `tmux-server`, `readline`), plus `setup.sh` and `Makefile`.
- Only four symlinks exist in `$HOME`: `.bashrc`, `.tmux.conf`, `.vimrc`, and
  `.dotfiles`.
- The `claude` package is **not stowed**. `~/.claude/settings.json` is a standalone
  file with five keys, and there are no hooks or commands. `~/.claude.json` has
  no MCP servers.
- Claude Code is installed in `~/.local/bin` (by hand, not by `setup.sh`).
  A `claude remote-control` process and several sessions are running.
  Restarting it drops live sessions, so schedule that step.
- **Missing:** Node/npx, `mise`, Chromium, `jq`, `opencode`, and
  `~/.secrets/context7-api-key`. Present: `stow`, `tmux`, `python3`.
- Ubuntu's `chromium` and `chromium-browser` apt packages are snap stubs, and snap
  is not set up.
- By design the server profile has no mise toolset (see `AGENTS.md`, "setup.sh
  design principles"), so Node is absent for a documented reason, not by accident.

## Steps

Each step is independently shippable. Do them in order.

### 1. Get up to speed

Bring the VPS to current `main` before adding anything.

- [ ] Read the diff first:
  `git diff HEAD origin/main -- setup.sh Makefile packages/bashrc-server packages/tmux-server packages/readline`
- [ ] Back up `~/.bashrc`, `~/.tmux.conf`, `~/.vimrc`, and `~/.claude/settings.json`.
- [ ] `git pull --ff-only`, then `make stow-server`. Run it in a fresh shell and
  keep the existing SSH session open until a second login works.
- [ ] Check that `tmux`, the Bash prompt, and the `tmx` helper still behave, and
  that the running remote-control process was not affected.
- [ ] Decide whether to also run `bash setup.sh --server --update` (idempotent)
  or leave `setup.sh` alone and only stow.
- [ ] Record the result and the current `main` commit in this file.

### 2. Stow the Claude config

- [ ] Add `STOW_INCLUDE = claude` to the VPS's untracked
  `${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/local.mk`, then `make stow`
  (or `make restow`).
- [ ] Remove or move the existing standalone `~/.claude/settings.json` first, or
  stow will refuse to replace it.
- [ ] Decide what the server should inherit. The workstation `settings.json` has
  `Bash(*)`, `WebFetch(*)`, `Edit` and `Write` auto-allowed. Confirm that is
  acceptable on a remote box before stowing, or add a server-specific
  override.
- [ ] Note that the `/pr` command and hooks come along with the package.
- [ ] Restart only new sessions to pick this up. `settings.json` is read at
  startup.

### 3. Toolchain: Node, jq

Node is required by `npx @playwright/mcp` and `npx @upstash/context7-mcp`.

- [ ] Decide how to get Node: `mise` (matches the workstation and
  `docs/plans/mise-node-migration.md`), or the distro/NodeSource package for a
  lighter footprint. The server profile deliberately skips mise today, so
  choose one and document it.
- [ ] Install `jq` (needed by `scripts/setup-claude-mcp.sh`).
- [ ] Make sure `node`/`npx` are on `PATH` for **non-interactive** shells too.
  Claude spawns MCP servers through `sh -c`, and the earlier check found `claude`
  itself only on the login-shell `PATH`.

### 4. Secrets

- [ ] Create `~/.secrets/` with mode 700 and copy the Context7 key to
  `~/.secrets/context7-api-key` with mode 600. The user does this by hand; never
  commit it or pass it through chat.

### 5. Playwright and Context7 MCP

- [ ] Install a browser for Playwright. Preferred: Playwright-managed Chromium
  (`npx playwright install --with-deps chromium`, needs sudo for system libs),
  which Playwright supports on Ubuntu 24.04. Alternative: Google Chrome `.deb`
  from Google's apt repo. Do not rely on the snap stub.
- [ ] Update `scripts/setup-claude-mcp.sh`:
  - make the browser path configurable instead of hardcoding `/usr/bin/chromium`
    (or drop `--executable-path` when using Playwright's own browser)
  - register only the headless server on the VPS (no display, so no
    `playwright-headed`), for example behind an environment variable or a
    `--headless-only` flag
  - revisit the hardcoded Chrome 157 user agent so it matches the browser
    actually installed
- [ ] Run the script as the login user, then check `claude mcp list` shows
  `playwright` and `context7` as connected.
- [ ] Smoke test headless navigation to a plain page, then to a bot-protected
  one.
- [ ] Watch memory with several Claude sessions open. With limited
  RAM, consider a swap file or a `--isolated`/short-lived browser setting
  if Chromium gets OOM-killed.
- [ ] Expect more bot challenges than on the workstation: the datacenter IP is
  itself a signal. If it is bad, evaluate a search-API MCP (Brave, Exa, Tavily)
  or a hosted browser instead of fighting the IP.
- [ ] Restart the `claude remote-control` process at a quiet moment so newly
  spawned sessions get the MCP servers. Existing sessions will not.

### 6. Make it reproducible (optional follow-up)

Only after steps 1-5 work by hand.

- [ ] Fold the working steps into an opt-in layer, such as
  `setup.sh --server --agent` (or a documented `make` target), so a rebuilt VPS
  gets Node, `jq`, the browser, the stowed `claude` package, and the MCP
  registration without manual notes.
- [ ] Keep it idempotent and non-fatal for optional pieces, in line with the
  `setup.sh` design principles.
- [ ] Extend the server test harness (`scripts/test-server.py`,
  `docker/test.sh -p server`) so the new layer is exercised.
- [ ] Update `AGENTS.md` (setup design principles and the structure tree) and,
  if the overview changes, the `README.md` package table.

## Open questions

- Node via mise or via distro packages on the server?
- Should the server's Claude permissions be stricter than the workstation's?
- Playwright-managed Chromium or Google Chrome `.deb`?
- Is swap needed on this small box?
- Is the `opencode` CLI wanted on the VPS at all? (Currently no.)

## Related

- `scripts/setup-claude-mcp.sh` registers the workstation MCP servers.
- `docs/plans/mise-node-migration.md` covers Node handling on the workstation.
- `docs/plans/archive/server-profile.md` describes the original server profile.
