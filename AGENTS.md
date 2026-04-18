# AGENTS.md

Technical reference for AI coding assistants working in this repository.

## Purpose

This repo bootstraps a personal development environment on Fedora 42+ and
Ubuntu 22.04+. It uses GNU Stow for dotfile symlinking and a single Bash
script (`setup.sh`) for installation.

It supports both native Linux and WSL2 environments. The base install flow is
shared across both; WSL-specific behavior must stay behind runtime detection or
live in `docs/SETUP_WSL.md`.

## Repo structure

```
dotfiles/
├── setup.sh                  # Main bootstrap script
├── Makefile                  # Stow link/unlink targets
├── docker-run.sh             # Drop into a test container
├── docker-compose.yml        # Fedora 42+ + Ubuntu 24.04 test containers
├── Dockerfile.fedora
├── Dockerfile.ubuntu
├── docs/                     # Project documentation and backlog
│   ├── INBOX.md              # Triage intake — process and clear regularly
│   ├── BACKLOG.md            # Deferred ideas and planned features
│   ├── plans/                # Detailed implementation plans
│   │   └── archive/          # Completed plans kept for reference
│   ├── SETUP_WSL.md          # WSL2-specific setup notes
├── bashrc-server/.bashrc     # Stow package: minimal Bash config for servers
├── vim-server/.vimrc         # Stow package: minimal Vim config for servers
├── zshrc/.zshrc              # Stow package: zsh config
├── zprofile/.zprofile        # Stow package: login shell environment
├── tmux-server/.tmux.conf    # Stow package: tmux config for server installs
├── tmux/.tmux.conf           # Stow package: tmux config
├── nvim/.config/nvim/        # Stow package: Neovim config
├── kitty/.config/kitty/      # Stow package: Kitty terminal config
├── opencode/                 # Stow package: opencode AI config
│   └── .config/opencode/
│       └── opencode.jsonc
└── scripts/                  # Repo-only utilities (not stowed)
    └── tmux-panes.sh
```

## Stow package convention

Each dotfile package is a directory at the repo root. Its internal layout
mirrors the structure expected under `$HOME`. For example:

```
bashrc-server/.bashrc  → stowed to ~/.bashrc
vim-server/.vimrc      → stowed to ~/.vimrc
zshrc/.zshrc           → stowed to ~/.zshrc
nvim/.config/nvim/     → stowed to ~/.config/nvim/
```

All packages are stowed to `$HOME` via `make stow`. The stowed packages are:
`zshrc`, `bashrc-server`, `vim-server`, `zprofile`, `tmux`, `tmux-server`, `nvim`, `kitty`, `opencode`.

The `scripts/` directory is a repo-only utility — it is NOT stowed.

## setup.sh design principles

- **Single entrypoint**: `bash setup.sh [--server | --slim | --full]`
- **Idempotent**: Every step is guarded with `command -v`, `[ -d ]`, or `[ -f ]` checks. Safe to run multiple times.
- **OS detection**: Detects Fedora (dnf) or Ubuntu/Debian (apt) via `/etc/os-release`. Fails clearly on unsupported distros.
- **WSL2 awareness**: Detects WSL2 via `/proc/version` for informational logging only. No WSL-specific install logic in `setup.sh`.
- **Server profile**: `--server` is Bash-first and intended for remote/headless systems. It installs only minimal operational tooling and server-specific dotfiles.
- **Kitty install path**: Installs pinned upstream kitty in the `--full` profile on native Linux instead of relying on distro package versions.
- **Non-fatal optional packages**: Each optional package in `--full` is installed with `|| warning` so a single missing package does not abort the run.

## Environment policy

- Support both native Linux and WSL2.
- Keep the default setup portable across both environments.
- Do not apply WSL-specific behavior unless runtime WSL detection confirms it.
- Do not add WSL-specific install branches to `setup.sh`.
- Put WSL-only quirks in guarded dotfiles or in `docs/SETUP_WSL.md`.
- Do not apply WSL-only workarounds on native Linux.

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
- Do not add WSL-specific logic to `setup.sh` — WSL quirks belong in `docs/SETUP_WSL.md` and in the dotfiles themselves when guarded by runtime detection.
- Do not stow `scripts/` — it is intentionally a repo-only utility.
- Do not hardcode UIDs or usernames — use `$USER`, `$HOME`, `$(whoami)` where needed.
- Do not proactively create documentation files (*.md) or README files unless explicitly requested by the User. Always check `docs/INBOX.md` for incoming triaged work, then `docs/BACKLOG.md` for planned features or pending implementation plans.
- Do not run `make stow`, `make unstow`, `make restow`, `setup.sh`, or any command that modifies system state or symlinks without explicit user confirmation.

## Maintenance

- When adding or modifying a stow package, update:
  - The `What's included` table in `README.md`
  - The repo structure tree in `AGENTS.md`
  - The stowed packages list in `AGENTS.md`

## Testing

Use the provided Docker/Podman containers for clean environment testing:

```bash
bash docker-run.sh -d fedora   # drop into Fedora container
bash docker-run.sh -d ubuntu   # drop into Ubuntu 24.04 container
```

Primary test target is **Fedora 42+**. See `docs/SETUP_WSL.md` for WSL2-specific notes.
