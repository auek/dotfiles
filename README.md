# dotfiles

Automated setup of a development environment using a single Bash script and GNU Stow.

Supports both native Linux and WSL2 Linux environments. The base install flow
is shared; WSL-specific quirks are handled only where needed via runtime guards
in dotfiles and notes in `docs/SETUP_WSL.md`.

On Fedora, container tooling is Podman-based. Native Fedora installs Podman plus
Docker-compatible CLI support; WSL2 Fedora keeps container setup as a separate,
WSL-specific path documented in `docs/SETUP_WSL.md`.

## What's included

| Package | Contents |
|---|---|
| `zshrc` | Zsh config (Oh My Zsh, aliases, FZF, dev helpers) |
| `zprofile` | Login shell environment (PATH, NVM, DOCKER_HOST) |
| `tmux` | tmux config (gruvbox theme, vi keys, WSL clipboard) |
| `nvim` | Neovim config (Lazy.nvim, LSP, Treesitter, completion) |
| `kitty` | Kitty terminal config (zsh shell, Gruvbox theme) |
| `opencode` | OpenCode AI config (agents, models, watcher settings) |

## Prerequisites

- Fedora 42+ or Ubuntu 22.04+
- `git`
- Docker / Podman (optional, for container-based testing)

## Installation

Clone the repo and run `setup.sh`:

```bash
git clone <repo-url> ~/.dotfiles
cd ~/.dotfiles
bash setup.sh          # slim install (default)
bash setup.sh --full   # full install including dev tools
```

## Supported environments

- Native Fedora 42+ and Ubuntu 22.04+
- Fedora 42+ under WSL2

WSL-specific behavior should only apply when runtime detection confirms WSL.
Native Linux should not inherit WSL-only settings or workarounds.

### Profiles

| Flag | What it installs |
|---|---|
| `--slim` | curl, git, gcc, make, stow, tmux, zsh, kitty + JetBrains Mono (non-WSL), Oh My Zsh, zsh-autosuggestions, dotfiles, Podman + Docker-compatible CLI on native Fedora |
| `--full` | Everything in slim + exa, fzf, ripgrep, bat, htop, bob-nvim (stable), nvm, node LTS, tldr, llm |

After installation, restart your shell:

```bash
exec zsh -l
```

## Makefile

| Target | Description |
|---|---|
| `make stow` | Symlink all dotfile packages to `$HOME` |
| `make unstow` | Remove all symlinks |
| `make restow` | Unstow then stow (useful after adding new files) |

## Docker testing

A Fedora and Ubuntu 24.04 container are available for testing the setup
in a clean environment without touching your host.

```bash
# Drop into a Fedora container
bash docker-run.sh -d fedora

# Drop into an Ubuntu container
bash docker-run.sh -d ubuntu
```

Inside the container, run `setup.sh` manually:

```bash
bash /home/devuser/code/dotfiles/setup.sh --slim
bash /home/devuser/code/dotfiles/setup.sh --full
```

### Docker reference

```bash
# Connect to a running container
docker compose exec dotfiles-fedora bash
docker compose exec dotfiles-ubuntu bash

# Stop and remove containers
docker compose down

# Remove images
docker rmi auek/dotfiles:fedora
docker rmi auek/dotfiles:ubuntu
```

See `docs/SETUP_WSL.md` for WSL2-specific setup notes and workarounds.
