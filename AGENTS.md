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
│   ├── palettes/             # One JSON palette per theme
│   └── templates/            # One template per fragment (per-theme overrides supported)
└── packages/                 # GNU Stow package sources
    ├── bashrc-server/.bashrc # Minimal Bash config for servers
    ├── vim-server/.vimrc     # Minimal Vim config for servers
    ├── zshrc/.zshrc          # Zsh config and portable tmx sessions with optional local hooks
    ├── zprofile/.zprofile    # Login environment and opt-in Arch tty1 Hyprland autostart
    ├── tmux-server/.tmux.conf # Server tmux config; new panes/windows inherit cwd
    ├── tmux/.tmux.conf       # Workstation tmux config; cwd inheritance and RGB
    ├── nvim/.config/nvim/    # Neovim config
    ├── nvim-work/.config/nvim/ # Opt-in editor with Telescope, nvim-tree, and selected theme
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
`mise`, and `tealdeer`. The `mise` package defaults to Node 24.19.0 and selects
latest stable Aqua releases of Neovim, Bat, eza, Tealdeer, Lazygit, fastfetch,
ripgrep, fd, and fzf. A machine may override Node or add optional tools with an
ordinary, untracked `~/.config/mise/config.local.toml` (`node = "lts"` and
`"aqua:astral-sh/uv" = "latest"` on the Arch workstation).
Do not Stow that file or change the shared pin for a machine-local preference.
Project version files still override either global default.
The shared Zsh `tmx` command lists sessions when called without arguments;
`tmx <name> [directory]` attaches/switches or creates in the supplied directory
(current directory by default). New sessions have one window/pane unless an
ordinary, untracked `${XDG_CONFIG_HOME:-$HOME/.config}/tmx/init.zsh` hook customizes
them. The hook runs in a separate `zsh -ef` process with session/window/pane IDs
and the absolute directory as arguments; it never runs on reattachment. No
editor or assistant is launched by shared code. Never Stow the local hook.
Bob configuration remains optional for rollback; it is not in the default
package selection. The separate `nvim-work` package is opt-in
via direct Stow; it
targets the same `~/.config/nvim` location as `nvim` and must not be stowed
together with it. It needs no default editor or theme packages. Basic editing works
without plugins; Lazy bootstraps on first launch and installs pinned Telescope
and Plenary plus nvim-tree, Everforest, Gruvbox, Mason, nvim-lspconfig,
telescope-fzf-native (built with Make and GCC/Clang), and vim-tmux-navigator.
The minimal profile shares the existing tmux navigation bindings and never saves
buffers automatically on pane switches. Use standard `:Lazy`
commands afterward. Profile colors follow the existing `theme-set` runtime
selection, defaulting to Everforest without the optional `themes` package. Plugin files and Lazy
state/lockfile are separate from the default profile. Text search needs `rg`.
Mason installs servers only on explicit request (`typescript-language-server`,
`css-lsp`, `yaml-language-server`) into the separate `nvim-work/mason` data root.
The minimal profile enables only available `ts_ls`, `cssls`, and `yamlls` servers,
with Azure Pipelines YAML schema associations. It adds no format-on-save or
completion framework. Startup installs missing plugins but does not check for updates. Default package selection remains unchanged. `make stow-hyprland`
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

Run `python3 scripts/test-nvim-work.py /absolute/path/to/nvim` to validate the
minimal profile through Stow in disposable homes (requires GNU Stow and Neovim).
It checks subprocess-free startup, native/mocked WSL clipboard selection and
UTF-8 data handling, safe reloads, buffer closing, and package removal. It does
not validate the real Windows clipboard or the default plugin profile. An optional
second argument points to pre-fetched `lazy.nvim`, `telescope.nvim`,
`plenary.nvim`, `nvim-tree.lua`, `everforest-nvim`, `gruvbox.nvim`, `mason.nvim`,
`nvim-lspconfig`, built `telescope-fzf-native.nvim`, and `vim-tmux-navigator` fixture
directories to check real Telescope file/text search (requires `rg`), including
space-separated path terms and incremental query edits, tree
opening (including `nvim .` and `:edit directory`), theme selection/reloading,
and offline startup with plugins installed.
An optional third argument supplies a Mason server fixture plus a local copy of
the Azure Pipelines schema to test real LSP behavior without network access.

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
