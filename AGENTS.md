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
│   ├── setup_hyprland.md     # Fedora Hyprland manual setup
│   ├── setup_wsl.md          # WSL2-specific setup notes
├── scripts/                  # Repo-only utilities: theme generator, palettes, templates, misc scripts
│   ├── generate-themes.py    # Render palettes x templates into theme packs (generate/check)
│   ├── palettes/             # One JSON palette per theme
│   └── templates/            # One template per fragment (per-theme overrides supported)
└── packages/                 # GNU Stow package sources
    ├── bashrc-server/.bashrc # Minimal Bash config for servers
    ├── vim-server/.vimrc     # Minimal Vim config for servers
    ├── zshrc/.zshrc          # Zsh config
    ├── zprofile/.zprofile    # Login shell environment
    ├── tmux-server/.tmux.conf # tmux config for server installs
    ├── tmux/.tmux.conf       # tmux config
    ├── nvim/.config/nvim/    # Neovim config
    ├── bob/.config/bob/      # Bob Neovim version-manager config
    ├── foot/.config/foot/    # Foot terminal config
    ├── themes/.local/        # Theme packs plus theme-set, swaybg-current, and foot-reload commands
    ├── gtk/.config/          # GTK3 and GTK4 theme settings
    ├── hypr/.config/         # Hyprland Lua config and session systemd units (cliphist, swaybg)
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
`zshrc`, `zprofile`, `tmux`, `nvim`, `foot`, `themes`, `hypr`, `waybar`,
`wofi`, `mako`, `opencode`, `claude`, `espanso`, and `bob`. Server packages use
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

## setup.sh design principles

- **Single entrypoint**: `bash setup.sh [--server | --slim | --full]`
- **Idempotent**: Every step is guarded with `command -v`, `[ -d ]`, or `[ -f ]` checks. Safe to run multiple times.
- **OS detection**: Detects Fedora (dnf) or Ubuntu/Debian (apt) via `/etc/os-release`. Fails clearly on unsupported distros.
- **WSL2 awareness**: Detects WSL2 via `/proc/version` for informational logging only. No WSL-specific install logic in `setup.sh`.
- **Server profile**: `--server` is Bash-first and intended for remote/headless systems. It installs only minimal operational tooling and server-specific dotfiles.
- **Non-fatal optional packages**: Each optional package in `--full` is installed with `|| warning` so a single missing package does not abort the run.

## Environment policy

- Support both native Linux and WSL2.
- Keep the default setup portable across both environments.
- Do not apply WSL-specific behavior unless runtime WSL detection confirms it.
- Do not add WSL-specific install branches to `setup.sh`.
- Put WSL-only quirks in guarded dotfiles or in `docs/setup_wsl.md`.
- Do not apply WSL-only workarounds on native Linux.

## Hyprland policy

- Hyprland and related desktop components remain under evaluation and are not
  installed by any `setup.sh` profile.
- Keep manual Hyprland setup requirements and package installation instructions
  in `docs/setup_hyprland.md`.

## Repository visibility

- This repository is public.
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

Use the provided Docker/Podman containers for clean environment testing:

```bash
bash docker/test.sh -d arch -p server  # validate Arch server setup twice
bash docker/run.sh -d fedora            # drop into Fedora container
bash docker/run.sh -d ubuntu            # drop into Ubuntu 24.04 container
```

Primary test target is **Fedora 42+**. See `docs/setup_wsl.md` for WSL2-specific notes.
