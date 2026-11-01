# AGENTS.md

Technical reference for AI coding assistants working in this repository.

## Purpose

This repo bootstraps a personal development environment on Arch Linux, Fedora
42+, and Ubuntu 24.04+. It uses GNU Stow for dotfile symlinking and a single Bash
script (`setup.sh`) for installation.

It supports both native Linux and WSL2 environments. The base install flow is
shared across both; WSL-specific behavior must stay behind runtime detection or
live in `docs/setup_wsl.md`.

## Repo structure

```
dotfiles/
├── setup.sh                  # Main bootstrap script
├── Makefile                  # Stow link/unlink targets
├── docker/                   # Container test harness
│   ├── compose.yml           # Arch, Fedora 42+, and Ubuntu 24.04 test containers
│   ├── Dockerfile.arch
│   ├── Dockerfile.fedora
│   ├── Dockerfile.ubuntu
│   ├── run.sh                # Drop into a test container
│   └── test.sh               # Recreate and validate a setup profile
├── docs/                     # Project documentation and backlog
│   ├── INBOX.md              # Triage intake — process and clear regularly
│   ├── backlog.md            # Deferred ideas and planned features
│   ├── plans/                # Detailed implementation plans
│   │   └── archive/          # Completed plans kept for reference
│   ├── setup_hyprland.md     # Arch desktop setup, migration, and customization
│   ├── setup_wsl.md          # WSL2-specific setup notes
├── scripts/                  # Repo-only utilities: theme generator, palettes, templates, misc scripts
│   ├── generate-themes.py    # Render palettes x templates into theme packs (generate/check)
│   ├── configure-hyprland.sh # Preserve local entrypoint and opt into tty1 autostart
│   ├── test-hyprland-bootstrap.py # Isolated bootstrap and login-guard checks
│   ├── test-tmx.py           # Isolated Zsh session/local-hook checks with private tmux sockets
│   ├── test-nvim.py          # Shared editor, local settings, clipboard, plugins, and LSP fixtures
│   ├── test-nvim-project-tools.py # Real project-local Prettier/ESLint and forbidden-fallback checks
│   ├── palettes/             # One JSON palette per theme
│   └── templates/            # One template per fragment (per-theme overrides supported)
└── packages/                 # GNU Stow package sources
    ├── bashrc-server/.bashrc # Minimal Bash config for servers
    ├── vim-server/.vimrc     # Minimal Vim config for servers
    ├── zshrc/.zshrc          # Zsh startup, private environment overrides, and portable tmx sessions
    ├── zprofile/.zprofile    # Login shim PATH and opt-in Arch tty1 Hyprland autostart
    ├── tmux-server/.tmux.conf # Server tmux config; new panes/windows inherit cwd
    ├── tmux/.tmux.conf       # Workstation tmux config; cwd inheritance and RGB
    ├── nvim/.config/nvim/    # Shared editor with optional project-local Prettier/ESLint
    ├── mise/.config/mise/    # Shared Node pin and stable editor/CLI baseline (including eza)
    ├── tealdeer/.config/tealdeer/ # tldr downloads use the system trust store
    ├── bob/.config/bob/      # Optional legacy Bob config for rollback
    ├── foot/.config/foot/    # Foot terminal config
    ├── themes/.local/        # Theme packs (including tmux modes/menus) plus theme-set, swaybg-current, and foot-reload
    ├── gtk/.config/          # GTK3 and GTK4 theme settings
    ├── hypr/.config/         # Hyprland Lua config, custom Swedish (US) keymap, activity-based media controls, and session systemd units (cliphist, swaybg)
    ├── waybar/.config/waybar/
    ├── wofi/.config/wofi/
    ├── mako/.config/mako/
    ├── opencode/.config/opencode/  # Commands (/pr), agents, MCP, permissions, watcher
    ├── claude/.claude/
    └── espanso/.config/espanso/
```

## Stow package convention

Each dotfile package is a directory directly under `packages/`. Its internal
layout mirrors the structure expected under `$HOME`. For example:

```
packages/bashrc-server/.bashrc  → stowed to ~/.bashrc
packages/vim-server/.vimrc      → stowed to ~/.vimrc
packages/zshrc/.zshrc           → stowed to ~/.zshrc
packages/nvim/.config/nvim/     → stowed to ~/.config/nvim/
```

The default workstation packages are stowed to `$HOME` via `make stow`:
`zshrc`, `zprofile`, `tmux`, `nvim`, `themes`, `opencode`, `claude`, `espanso`,
`mise`, and `tealdeer`. The shared `nvim` profile provides LSP/snippet/path/buffer
completion, Git indicators, selected Treesitter highlighting, search/tree,
themes, status line, key hints, pairs/surround, and safe tmux navigation.
`features.format_on_save` enables project-local Prettier through Conform;
`features.eslint` enables project-local ESLint CLI diagnostics through pinned
nvim-lint on open/save. Both default off. Diagnostics never apply fixes.
Executable discovery stops at the repository root (or nearest package outside
Git) and supports hoisted dependencies. Missing tools skip the integration.
Never add global/PATH, Mason, mise, `npx` auto-download, or LSP fallbacks for
project formatters/linters such as Prettier and ESLint. Project configuration,
plugins, parsers, and ignore rules belong to the project's dependency workflow.
Do not enable the optional ESLint language server; use `features.eslint`.
Other filetypes have no implicit save formatter, including the former
Lua/Python and generic LSP fallbacks.
`format_timeout_ms` defaults to 3000 and accepts local integer overrides from
1 to 60000. A failure or timeout preserves the buffer and never changes tools.
It has no assistant completion provider or separate Git command plugin.
Telescope 0.2.1 is pinned for native Treesitter previews; do not revert to the
0.1.8 previewer, which calls APIs removed by the supported Treesitter rewrite.
The `mise` package defaults to Node 24.19.0 and selects
latest stable Aqua releases of Neovim, Bat, eza, Tealdeer, Lazygit, fastfetch,
ripgrep, fd, and fzf. A machine may override Node or add optional tools with an
ordinary, untracked `~/.config/mise/config.local.toml` (`node = "lts"` and
`"aqua:astral-sh/uv" = "latest"` on the Arch workstation).
Do not Stow that file or change the shared pin for a machine-local preference.
Project version files still override either global default.
`.zshrc` also sources an ordinary `~/.zshrc.private` at the end for local
environment overrides. Keep that file outside the repository; never Stow or
commit its contents.
Oh My Zsh initializes completion once after setting plugin paths; do not run
an earlier `compinit` or disable its audits. Login/interactive startup adds mise
shim PATH entries directly (respecting its data/shim and XDG overrides), then
interactive Zsh performs one full mise activation. Keep its initial environment
hook: deferring it only to improve an exit benchmark changes first-command behavior.
The shared Zsh `tmx` command lists sessions when called without arguments;
`tmx <name> [directory]` attaches/switches or creates in the supplied directory
(current directory by default). New sessions have one window/pane unless an
ordinary, untracked `${XDG_CONFIG_HOME:-$HOME/.config}/tmx/init.zsh` hook customizes
them. The hook runs in a separate `zsh -ef` process with session/window/pane IDs
and the absolute directory as arguments; it never runs on reattachment. No
editor or assistant is launched by shared code. Never Stow the local hook.
Bob configuration remains optional for rollback; it is not in the default
package selection. Neovim uses one `nvim` Stow package; machine-local options
live in an ordinary untracked `~/.config/nvim/local.lua` (respecting
`XDG_CONFIG_HOME`). Server maps merge, parser lists replace defaults, and
`server_options` supplies per-server overrides. Never Stow the local file.
The shared editor targets Neovim 0.12+. The baseline selects available `ts_ls`,
`cssls`, `yamlls`, and `bashls` servers
with Azure Pipelines YAML schemas. Mason installs servers/ShellCheck only on
explicit request; `:InstallParsers` installs explicitly selected parsers.
Treesitter uses the supported main-branch API, eager loading, native highlighting,
and the separate `stdpath("data")/treesitter-v2` parser/query root. Plugin updates
run `:TSUpdate` for existing parsers; startup never installs parsers. An old
installed legacy plugin stays dormant but remains in Lazy's update list until
an explicit `:Lazy update nvim-treesitter` and restart, keeping incompatible
query handlers out of Markdown hover windows. Restart before updating to load
that guard rather than hot-reloading a mix of legacy and supported modules.
Parser builds need standalone tree-sitter CLI 0.26.1+, curl/tar and a C compiler.
Do not add its current Aqua binaries to the shared mise baseline: Linux x86_64
0.26.1/0.27.1 require glibc 2.39, incompatible with RHEL 9's 2.34. CLI installation
is machine-local; README includes an opt-in Cargo source-build route whose
target-machine verification remains pending. The CLI is not a runtime dependency.
There is no automatic parser/server installation, shell formatting, or default
format-on-save. Formatting, ESLint diagnostics, and Markdown preview are separate opt-in
features. Lazy bootstraps and installs missing editor plugins, without update
checks or project-local plugin specs. Pins come from the tracked `lazy-lock.json`;
runtime lockfile/cache/state live under `stdpath("state")/dotfiles`. Plugin and
Mason roots remain `stdpath("data")/lazy` and `/mason`. Do not automatically
clean, migrate, or remove existing user data. For installations using the old
`nvim-work` package, unstow it before pulling its removal, then link `nvim`;
see README migration notes. Basic editing survives bootstrap failure. Theme
selection follows `theme-set` with Everforest/Habamax fallbacks; real Windows
clipboard behavior still needs manual verification. Default package selection
remains unchanged. `make stow-hyprland`
additionally links the desktop group: `foot`,
`hypr`, `waybar`, `wofi`, and `mako`. It does not install software or enable
autostart; `setup.sh --hyprland` handles those steps. General Stow operations
do not remove existing desktop links. The `themes` package
also supplies tmux selector, copy-mode, menu, and popup styles. The `hypr` media
bindings use `playerctl` and `playerctld` to control the most recently active
player. The `hypr` package also supplies a Swedish (US) keymap with
`Right Alt + E` for é and `Right Alt + Shift + E` for É. Server packages use
`make stow-server`. The external-theme dependent `gtk` package is opt-in via
`make stow-gtk`.

The `themes` package installs static assets under
`~/.local/share/dotfiles/themes` and the `theme-set` command under
`~/.local/bin`. Each theme pack holds one native fragment per supported
component (`foot.ini`, `tmux.conf`, `nvim.lua`, `waybar.css`, `hyprland.lua`,
`wofi.css`, `mako.conf`, `swaybg-color`, `wallpaper-name`); application base
configs keep layout
and behavior and import only their fragment through the runtime `current` path.
`theme-set` validates a pack completely before switching and swaps the symlink
atomically. Theme selection is runtime state at
`~/.local/state/dotfiles/theme/current`; it must not be stored in the worktree.

The `scripts/` directory is a repo-only utility — it is NOT stowed. Theme
fragments are generated from the JSON palettes in `scripts/palettes/` and the
templates in `scripts/templates/` with `scripts/generate-themes.py`. Use
`make themes-generate` after editing a palette or template and
`make themes-check` to verify checked-in fragments are current.

Theme reloads are independent and best-effort. tmux, Waybar, Mako, Hyprland,
wallpaper, and running Foot terminals update immediately where available;
Wofi and new Foot instances load the selection at launch. Neovim reloads on
focus or with `:ReloadTheme`. A failed application reload does not revert the
validated selection.

## setup.sh design principles

- **Single entrypoint**: `bash setup.sh [--server | --slim | --full] [--hyprland] [--update]`
- **Idempotent**: Every step is guarded with `command -v`, `[ -d ]`, or `[ -f ]` checks. Safe to run multiple times.
- **OS detection**: Detects Arch (pacman), Fedora (dnf), or Ubuntu/Debian (apt) via `/etc/os-release`. Fails clearly on unsupported distros.
- **WSL2 awareness**: Detects WSL2 via `/proc/version` for logging, native-only desktop validation, and the existing Fedora container-tooling guard. No WSL-specific package installation branches.
- **Server profile**: `--server` is Bash-first and intended for remote/headless systems. It installs only minimal operational tooling and server-specific dotfiles.
- **Non-fatal optional packages**: Each optional package in `--full` is installed with `|| warning` so a single missing package does not abort the run.

Full native Fedora installs Podman, Docker-compatible CLI support, and Compose;
WSL Fedora's container setup remains documented in `docs/setup_wsl.md`.
The full profile installs the declared mise tools on all supported distros;
it does not install overlapping distro packages, nvm, Bob, or the Python tldr
client. The slim/server profiles do not install the mise toolset. Existing
installations are retained; no migration removes user binaries or npm globals.
Stow, tmux, htop, shell frameworks, and Python applications such as llm keep
their existing installers. eza is part of the shared mise baseline; uv is
machine-local and is not installed separately by setup. RHEL is not supported
by `setup.sh`; limited RHEL machines use
direct Stow and `mise install` with their existing system tools. GNOME keybindings are
applied only when supported, including the Swedish (US) layout (`se+us`):
Right Alt + `[`, `;`, and `'` produce å, ö, and ä.

## Environment policy

- Support both native Linux and WSL2.
- Keep the default setup portable across both environments.
- Do not apply WSL-specific behavior unless runtime WSL detection confirms it.
- Do not add WSL-specific install branches to `setup.sh`.
- Put WSL-only quirks in guarded dotfiles or in `docs/setup_wsl.md`.
- Do not apply WSL-only workarounds on native Linux.

## Hyprland policy

- Native Arch Hyprland is supported through opt-in `--hyprland`, combined with
  slim/full. Reject server, non-Arch, and WSL combinations before installation.
- Hardware preparation belongs to the user: never provision GPU drivers,
  firmware, kernel modules, boot settings, or audio/Bluetooth system stacks.
- Keep shared configs hardware-neutral. Machine-specific GPU and monitor
  overrides belong in the local `~/.config/hypr/hyprland.lua` entrypoint.
- `scripts/configure-hyprland.sh` preserves existing entrypoints, creates the
  local `~/.local/state/dotfiles/hyprland/autostart` marker, and attempts a user
  daemon reload. It must not start a desktop or session services during setup.
- `.zprofile` requires that marker for guarded Arch tty1 autostart. Unlinking
  packages does not remove local preferences; re-running `--hyprland` opts in.
- Keep startup, migration, customization, and optional GTK theme instructions
  in `docs/setup_hyprland.md`. External GTK installation is not automated.

## Repository visibility

- This repository is public.
- Describe deployment targets by platform or constraints, such as "limited
  machine" or "Arch workstation". Keep employment and personal-device context
  out of documentation, commit messages, and pull request titles/descriptions.
- Never commit secrets, tokens, private keys, machine-specific credentials, or
  sensitive hostnames/IPs.
- Prefer placeholders, environment variables, or local untracked files for
  sensitive configuration.
- Be careful with command examples and captured output so they do not expose
  secret material.

## What not to do

- Do not put dotfiles outside of a stow package directory.
- Do not reintroduce Ansible or any external orchestration tool.
- Do not add WSL-specific logic to `setup.sh` — WSL quirks belong in `docs/setup_wsl.md` and in the dotfiles themselves when guarded by runtime detection.
- Do not stow `scripts/` — it is intentionally a repo-only utility.
- Do not hardcode UIDs or usernames — use `$USER`, `$HOME`, `$(whoami)` where needed.
- Do not proactively create documentation files (*.md) or README files unless explicitly requested by the User. Always check `docs/INBOX.md` for incoming triaged work, then `docs/backlog.md` for planned features or pending implementation plans.
- Do not run `make stow`, `make unstow`, `make restow`, `setup.sh`, or any command that modifies system state or symlinks without explicit user confirmation.

## Maintenance

- When adding or modifying a stow package, update:
  - The `What's included` table in `README.md`
  - The repo structure tree in `AGENTS.md`
  - The stowed packages list in `AGENTS.md`

## Testing

Hyprland verification status: isolated checks pass, and migration on the
existing Arch workstation has been smoke-tested through a logout/login.
Neither a fresh `setup.sh --hyprland` installation nor its Arch container
installation check has been run. Fresh-install verification is deferred until
the next Arch installation. Do not describe the full bootstrap as validated
based on the existing-session migration check.

Use the provided Docker/Podman containers for clean environment testing:

```bash
bash docker/test.sh -d arch -p server  # validate Arch server setup twice
bash docker/test.sh -d arch -p slim --hyprland # desktop bootstrap twice, no compositor
bash docker/run.sh -d fedora            # drop into Fedora container
bash docker/run.sh -d ubuntu            # drop into Ubuntu 24.04 container
```

`docker/test.sh` recreates the selected container and validates commands, login
shell, and Stow links after two setup runs. The Hyprland path also checks local
entrypoint preservation and the autostart marker. It does not test GPU support,
a graphical session, or portal functionality. Do not run it on the host as a
substitute for the container.

Run `python3 scripts/test-nvim.py /absolute/path/to/nvim` to validate the shared
profile through Stow in disposable homes (requires GNU Stow and Neovim).
It checks subprocess-free basic startup, native/mocked WSL clipboard and UTF-8
handling, safe reloads/buffer closing, local settings validation/merging, and
package removal preserving local files. An optional second argument supplies
the plugin repositories in `lazy-lock.json` (fzf-native already built) to check
real completion, Git indicators, parser configuration, Telescope search
(requires `rg`), tree/directory startup, theme reloads, optional features and
offline startup with plugins installed. An optional third argument supplies a
Mason fixture with the four baseline servers, ShellCheck, and a local
`azure-schema.json` for real language-server and diagnostic checks without
network access. The tests never install into the real home; real Windows
clipboard and interactive terminal behavior remain manual checks.
An optional fourth argument provides a matching parser/query fixture (use `-`
for the Mason argument to skip LSP fixtures). Tests cover native Markdown hover
with TypeScript fences, injection parsing/conceal-line rendering, real LSP `gh`,
missing/old CLI warnings, and safe startup while a legacy plugin awaits update.
Preview regressions exercise asynchronous TypeScript/Bash/Markdown file reads,
native highlighting, missing-parser syntax fallback, and a real visible
Telescope picker preview window (not only result-list matching).

`scripts/test-nvim-project-tools.py` runs actual Conform/nvim-lint save/open
hooks in disposable homes. Supply Neovim, pinned Lazy/Conform/nvim-lint fixtures, two
Prettier npm fixture prefixes, and ESLint 8/9 fixture prefixes with compatible
`@typescript-eslint/parser` dependencies. It checks real JS/TS/CSS/etc. formatting,
legacy/flat ESLint configs, monorepo version selection, ignores, visible errors,
and no global/cwd/other-repository/LSP fallback. Tests use existing project
dependencies and perform no downloads or real-home changes.

Run the lightweight isolated checks with:

```bash
python3 scripts/test-hyprland-bootstrap.py
python3 scripts/test-tmx.py
bash -n setup.sh scripts/configure-hyprland.sh docker/test.sh
zsh -n packages/zprofile/.zprofile
make themes-check
```

The Python checks use disposable homes and mocked commands in the system
temporary directory; they do not execute host setup, Stow, or service-manager
operations. The `tmx` checks require Zsh and tmux and use real private tmux
sockets with attach/switch commands mocked; they never access host sessions.
They cover listing, exact-name attachment, directory handling, 80/20 and 50/50
hooks, program startup, hook isolation/failures, and terminal-size fallbacks.
Python's `tempfile` manages creation and cleanup, with no dependency on an
agent-specific directory.

`scripts/test-mise.py` checks real mise activation, first-command Node/npm/npx
and Neovim selection, machine-local Node overrides, project Node version files,
inherited subprocess PATHs, PATH deduplication, declarative bootstrap behavior,
and Stow conflicts/removal
in disposable homes. Pass the mise executable, unpacked Node 24.19.0 and
another Node installation root, and a disposable fixture's
`installs/aqua-neovim-neovim` directory produced by a real Aqua install.
It copies the Neovim fixture and registers the supplied Node builds locally;
it performs no downloads or host installation. This does not validate the
proxy configuration, target-machine performance, or the full container bootstrap.

`docker/run.sh -d <distro> -t <server|slim|full>` runs setup and opens a shell.
For an already-running test container:

```bash
docker compose -f docker/compose.yml exec dotfiles-arch bash
```

Use `docker compose -f docker/compose.yml down` to remove the test containers.
Primary general test target is **Fedora 42+**; desktop bootstrap targets Arch.
See `docs/setup_wsl.md` for WSL2-specific notes.
