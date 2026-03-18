# AGENTS.md

Technical reference for AI coding assistants working in this repository.

## Purpose

This repo bootstraps a personal development environment on Fedora 40+ and
Ubuntu 22.04+. It uses GNU Stow for dotfile symlinking and a single Bash
script (`setup.sh`) for installation.

## Repo structure

```
dotfiles/
├── setup.sh                  # Main bootstrap script
├── Makefile                  # Stow link/unlink targets
├── docker-run.sh             # Drop into a test container
├── docker-compose.yml        # Fedora 42 + Ubuntu 24.04 test containers
├── Dockerfile.fedora
├── Dockerfile.ubuntu
├── docs/                     # Project documentation and backlog
│   ├── BACKLOG.md            # Planned features and ideas
│   ├── plans/                # Detailed implementation plans
│   └── SETUP_WSL.md          # WSL2-specific setup notes
├── zshrc/.zshrc              # Stow package: zsh config
├── zprofile/.zprofile        # Stow package: login shell environment
├── tmux/.tmux.conf           # Stow package: tmux config
├── nvim/.config/nvim/        # Stow package: Neovim config
├── aider/                    # Stow package: aider AI config
│   ├── .aider.conf.yml
│   ├── .aider.model.settings.yml
│   └── ARCHITECT.md          # Aider-specific persona/context (not for general use)
└── scripts/                  # Repo-only utilities (not stowed)
    └── tmux-panes.sh
```

## Stow package convention

Each dotfile package is a directory at the repo root. Its internal layout
mirrors the structure expected under `$HOME`. For example:

```
zshrc/.zshrc          → stowed to ~/.zshrc
nvim/.config/nvim/    → stowed to ~/.config/nvim/
```

All packages are stowed to `$HOME` via `make stow`. The stowed packages are:
`zshrc`, `zprofile`, `tmux`, `nvim`, `aider`.

The `scripts/` directory is a repo-only utility — it is NOT stowed.

## setup.sh design principles

- **Single entrypoint**: `bash setup.sh [--slim | --full]`
- **Idempotent**: Every step is guarded with `command -v`, `[ -d ]`, or `[ -f ]` checks. Safe to run multiple times.
- **OS detection**: Detects Fedora (dnf) or Ubuntu/Debian (apt) via `/etc/os-release`. Fails clearly on unsupported distros.
- **WSL2 awareness**: Detects WSL2 via `/proc/version` for informational logging only. No WSL-specific install logic in `setup.sh`.
- **Non-fatal optional packages**: Each optional package in `--full` is installed with `|| warning` so a single missing package does not abort the run.

## What not to do

- Do not put dotfiles outside of a stow package directory.
- Do not reintroduce Ansible or any external orchestration tool.
- Do not add WSL-specific logic to `setup.sh` — WSL quirks belong in `docs/SETUP_WSL.md` and in the dotfiles themselves (they already have WSL guards).
- Do not stow `scripts/` — it is intentionally a repo-only utility.
- Do not hardcode UIDs or usernames — use `$USER`, `$HOME`, `$(whoami)` where needed.
- Do not proactively create documentation files (*.md) or README files unless explicitly requested by the User. Always check `docs/BACKLOG.md` for planned features or pending implementation plans.

## Testing

Use the provided Docker/Podman containers for clean environment testing:

```bash
bash docker-run.sh -d fedora   # drop into Fedora 42 container
bash docker-run.sh -d ubuntu   # drop into Ubuntu 24.04 container
```

Primary test target is **Fedora 42**. See `docs/SETUP_WSL.md` for Podman setup on WSL2.
