# Implementation Plan: Agent tooling on the VPS

Status: done (2026-11-17). Written 2026-11-15 after Playwright MCP landed on the
workstation (`feat/playwright-mcp`). Steps 1-5 were carried out by hand on the VPS
and verified with a real Playwright MCP session; step 6 (a reproducible layer) was
deliberately left out. Context7 is not set up on the VPS.

## Goal

Give Claude Code on the VPS the same capabilities as on the workstation,
starting with Playwright MCP and Context7, and make the VPS reproducible from
this repository so it stops drifting. The VPS is used remotely through
`claude remote-control`, so reliability matters more than polish.

The immediate need turned out to be narrower: Claude on the VPS stopped asking
for permission on every action, and could browse bot-protected shopping and price
sites (Prisjakt, Amazon) that plain `curl` only partly serves.

## Outcome

- **Permissions.** The `claude` package is optional and was never applied on the
  VPS, so `~/.claude/settings.json` had no `permissions` block and everything
  prompted. The baseline is now merged by running
  `scripts/setup-claude-settings.py` directly. `make stow-server` does not include
  the `claude` package, and `make restow` stows the desktop group, so neither
  applies it on a server.
- **Repo and shell.** `~/code/dotfiles` follows `main`. `make stow-server` needed
  the old `~/.inputrc` moved aside first (it was a regular file, not a link).
- **Swap.** A 2 GB `/swapfile` with `vm.swappiness=10` was added (the box has
  3.7 GiB RAM, 2 CPUs and had no swap).
- **opencode.** The `opencode.service` user unit was stopped and disabled. The unit
  file and `~/.opencode` remain, so it can be re-enabled with
  `systemctl --user enable --now opencode`.
- **Playwright MCP.** Registered headless only, using Node 24 and Playwright's own
  Chromium. `scripts/setup-claude-mcp.sh --headless-only` registers it, and
  `scripts/install-playwright-apparmor.sh` installs the sandbox profile.
- **Permissions change.** `browser_evaluate` no longer prompts (it is how Claude
  reads page text). `browser_run_code_unsafe` and `browser_file_upload` still ask.
  The installed MCP names the tool `browser_run_code_unsafe`, so the old
  `browser_run_code` rule matched nothing; both names are listed.

## Findings

Initial state, as of 2026-11-15:

Host: Ubuntu 24.04, a small VPS (under 4 GB RAM), ample free disk, datacenter IP.

- Dotfiles lived in `~/code/dotfiles` on `main`, clean, **72 commits behind**
  `origin/main`. Nothing kept it fresh, unlike the workstation, where lazygit fetches
  and fast-forwards `main` in the background.
- Only four symlinks existed in `$HOME`: `.bashrc`, `.tmux.conf`, `.vimrc`, and
  `.dotfiles`.
- The `claude` package was **not stowed**, `~/.claude/settings.json` was a standalone
  file with five keys, and `~/.claude.json` had no MCP servers.
- Claude Code is installed in `~/.local/bin` (by hand, not by `setup.sh`), which is
  only on the login-shell `PATH`. A `claude remote-control` process and several
  sessions were running. Restarting it drops live sessions.
- **Missing:** Node/npx, `mise`, Chromium, `jq`, `opencode`, and
  `~/.secrets/context7-api-key`.
- Ubuntu's `chromium` and `chromium-browser` apt packages are snap stubs, and snap
  is not set up.
- By design the server profile has no mise toolset (see `AGENTS.md`, "setup.sh
  design principles"), so Node was absent for a documented reason.

## Steps

### 1. Get up to speed (done)

- [x] Read the diff, back up the existing dotfiles, `git pull --ff-only`.
- [x] `make stow-server`. It aborted on `~/.inputrc` (a regular file); the old file
  was saved as `~/.inputrc.bak` and the second run linked everything.
- [x] The "BUG in find_stowed_path" lines from Stow 2.4 are a harmless warning; the
  links are still created.
- [x] `setup.sh` was left alone; only stow was used.

### 2. Claude config (done, differently from the original plan)

- [x] The package is not stowed. The repo now merges
  `packages/claude/settings.base.json` into a real, machine-local
  `~/.claude/settings.json` (baseline keys win, app-written keys such as `theme`
  are kept). On the VPS, run `scripts/setup-claude-settings.py` after each pull,
  because the server stow group does not run it.
- [x] The server uses the same permissions as the workstation (`Bash(*)`,
  `WebFetch(*)`, `Edit` and `Write` allowed; `sudo`, `chmod`, `chown`, `dd` and
  force-push ask).
- [x] Settings are read at startup, so only new sessions pick up changes.

### 3. Toolchain: Node, jq (done)

- [x] Node comes from NodeSource (Node 24), not apt: Ubuntu 24.04's apt Node is 18,
  and Playwright needs 20 or later. Remove the apt `nodejs` and `npm` packages
  first, since the separate `npm` package conflicts with NodeSource's.
- [x] `jq` is installed from apt.
- [x] `/usr/bin/node` and `/usr/bin/npx` are on the non-interactive `PATH`, which
  matters because Claude starts MCP servers through `sh -c`.

### 4. Secrets (skipped)

- [ ] `~/.secrets/context7-api-key` (mode 600, created by hand, never committed or
  pasted into chat) is not created, so Context7 is not registered. The setup script
  skips it with a warning when the file is missing.

### 5. Playwright MCP (done)

- [x] Browser: Playwright-managed Chromium
  (`npx playwright install --with-deps chromium`), not the snap stub.
- [x] `scripts/setup-claude-mcp.sh --headless-only` registers only the headless
  server. Without the flag it skips the headed server when neither `DISPLAY` nor
  `WAYLAND_DISPLAY` is set.
- [x] The MCP defaults to the Google Chrome channel, which the VPS lacks. When
  `/usr/bin/chromium` is absent, the script points `--executable-path` at
  Playwright's Chromium, resolving the versioned path when the server starts so
  browser updates keep working.
- [x] Ubuntu 24.04 sets `kernel.apparmor_restrict_unprivileged_userns=1`, which makes
  Chromium fail with "No usable sandbox!". `scripts/install-playwright-apparmor.sh`
  installs `/etc/apparmor.d/playwright-chromium` (from
  `scripts/apparmor/playwright-chromium.in`), which allows user namespaces for
  Playwright's Chromium only, so the sandbox stays on and `--no-sandbox` is not
  needed. Run it as the login user; it calls `sudo`.
- [x] Smoke tests: Prisjakt renders fully through the MCP, and an Amazon.se front
  page loaded without a CAPTCHA from the datacenter IP. Memory is fine for one
  headless browser; do not run several in parallel on this box.
- [x] Restart Claude Code (and `claude remote-control`, at a quiet moment) so new
  sessions get the MCP servers. Existing sessions do not.
- Expect challenges on some sites. In a plain `curl` survey from the VPS, seven of
  ten shopping sites answered 200, three answered 403, and only PriceRunner was a
  real challenge (an AWS WAF JavaScript challenge, which needs a browser). If Amazon
  starts challenging the datacenter IP, route the browser through the home
  connection over Tailscale (exit node or SOCKS proxy), or evaluate a search-API MCP
  or a hosted browser.

### 6. Make it reproducible (not pursued)

Steps 1-5 work by hand, and a rebuilt VPS is rare, so the opt-in layer was not
built. If the VPS is rebuilt, repeat this plan in order, or fold the steps into
something like `setup.sh --server --agent`.

- [ ] An opt-in layer that installs Node, `jq`, the browser, the AppArmor profile,
  the Claude settings merge and the MCP registration, idempotent and non-fatal for
  optional pieces, in line with the `setup.sh` design principles.
- [ ] Extend the server test harness (`scripts/test-server.py`,
  `docker/test.sh -p server`) so that layer is exercised.
- [ ] Update `AGENTS.md` (setup design principles and the structure tree) and, if
  the overview changes, the `README.md` package table.

## Open questions (answered)

- Node via mise or via distro packages on the server? NodeSource, system-wide.
- Should the server's Claude permissions be stricter than the workstation's? No,
  the same baseline.
- Playwright-managed Chromium or Google Chrome `.deb`? Playwright-managed Chromium.
- Is swap needed on this small box? Yes, a 2 GB swapfile was added.
- Is the `opencode` CLI wanted on the VPS at all? No. The service is disabled, and
  the install is left in place in case it is wanted again.

## Related

- `scripts/setup-claude-mcp.sh` registers the MCP servers (`--headless-only` on
  servers).
- `scripts/install-playwright-apparmor.sh` installs the Chromium sandbox profile.
- `scripts/setup-claude-settings.py` merges the settings baseline.
- `docs/plans/mise-node-migration.md` covers Node handling on the workstation.
- `docs/plans/archive/server-profile.md` describes the original server profile.
