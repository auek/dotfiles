# dotfiles

Automated setup of a development environment using a single Bash script and GNU Stow.

Supports both native Linux and WSL2 Linux environments. The base install flow
is shared; WSL-specific quirks are handled only where needed via runtime guards
in dotfiles and notes in `docs/setup_wsl.md`.

On Fedora, container tooling is Podman-based. Native Fedora installs Podman plus
Docker-compatible CLI support in the `--full` profile; WSL2 Fedora keeps
container setup as a separate,
WSL-specific path documented in `docs/setup_wsl.md`.

## What's included

| Package | Contents |
|---|---|
| `zshrc` | Zsh config (Oh My Zsh, aliases, FZF, dev helpers) |
| `bashrc-server` | Minimal Bash config for remote/headless server installs |
| `vim-server` | Minimal Vim config for remote/headless server installs |
| `zprofile` | Login shell environment (PATH, NVM, DOCKER_HOST) |
| `tmux` | tmux config (switchable theme, vi keys, Wayland session environment, WSL clipboard) |
| `tmux-server` | tmux config for server installs (C-b prefix, no GUI clipboard assumptions) |
| `nvim` | Neovim config (switchable theme, Lazy.nvim, LSP, Treesitter, completion) |
| `foot` | Default Foot terminal configuration (zsh shell, switchable palette) |
| `themes` | Gruvbox and Everforest packs for Foot, tmux, Neovim, and Waybar, plus `theme-set` |
| `gtk` | Opt-in GTK3/GTK4 settings and libadwaita imports for the external Everforest theme |
| `hypr` | Hyprland Lua configuration (keybindings, Everforest styling, wallpaper, idle policy, clipboard history, systemd session target) |
| `waybar` | Switchable Waybar status bar (Hyprland workspaces, window title, audio, network, tray, clock) |
| `wofi` | Wofi application launcher (compact Everforest styling) |
| `mako` | Mako notifications (Everforest colors, urgency states, compact geometry) |
| `opencode` | OpenCode AI and TUI config (Everforest theme, agents, models, watcher settings) |

## Prerequisites

- Fedora 42+ or Ubuntu 22.04+
- `git`
- Docker / Podman (optional, for container-based testing)

### Hyprland bootstrap

`~/.config/hypr/hyprland.lua` is intentionally a local, regular file rather
than a Stow symlink. It requires the Stow-managed `dotfiles.lua`:

```lua
require("dotfiles")
```

Keeping the primary config outside the Git worktree prevents Hyprland from
generating a fallback stub when a branch change temporarily removes a managed
file.

The Hyprland session uses `swaybg` to load
`~/Pictures/Wallpapers/current.jpg` in fill mode. The image stays local rather
than being redistributed through this public repository. If it is absent,
`swaybg` uses the Everforest background color instead.

## Installation

Clone the repo and run `setup.sh`:

```bash
git clone <repo-url> ~/.dotfiles
cd ~/.dotfiles
bash setup.sh --server         # minimal remote/headless server install
bash setup.sh                   # slim install (default)
bash setup.sh --full            # full install including dev tools
bash setup.sh --full --update   # first-time bootstrap: also upgrades all system packages
```

## Supported environments

- Native Fedora 42+ and Ubuntu 22.04+
- Fedora 42+ under WSL2

WSL-specific behavior should only apply when runtime detection confirms WSL.
Native Linux should not inherit WSL-only settings or workarounds.

### Profiles

| Flag | What it installs |
|---|---|
| `--server` | curl, git, make, stow, tmux, vim, minimal Bash config, minimal Vim config, server tmux config |
| `--slim` | curl, gh, git, gcc, make, stow, tmux, zsh, Oh My Zsh, zsh-autosuggestions, dotfiles |
| `--full` | Everything in slim + Podman + Docker-compatible CLI on native Fedora, eza, fzf, ripgrep, bat, htop, bob-nvim (stable), nvm, node LTS, uv, tldr, llm |

After installation, restart your shell:

```bash
exec zsh -l
```

On GNOME-based Fedora installs, `setup.sh` also applies the preferred
`Swedish (US)` keyboard layout for a US keyboard workflow:

```bash
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'se+us')]"
```

This keeps the base layout as `US` while putting `å`, `ö`, and `ä` on
`Right Alt + [`, `Right Alt + ;`, and `Right Alt + '`.

## Makefile

| Target | Description |
|---|---|
| `make stow` | Symlink the default workstation packages to `$HOME` |
| `make stow-server` | Symlink only the server profile dotfiles to `$HOME` |
| `make stow-gtk` | Symlink the opt-in Everforest GTK settings after installing the external theme |
| `make unstow` | Remove the default workstation package symlinks |
| `make unstow-server` | Remove only the server profile symlinks |
| `make unstow-gtk` | Remove only the Everforest GTK settings symlinks |
| `make restow` | Restow the default workstation packages after adding files |

## Theme switching

Everforest is selected automatically the first time the workstation packages
are stowed. Switch all supported applications with one command:

```bash
theme-set gruvbox
theme-set everforest
theme-set            # prints the active theme
```

The command updates tmux and Waybar immediately. New Foot and Neovim instances
use the selected theme; live reloads for those applications are outside the
initial POC. Static theme packs live under `~/.local/share/dotfiles/themes`,
while the local `current` symlink lives under `~/.local/state/dotfiles/theme`
so switching themes does not modify the Git worktree.

## Docker testing

A Fedora and Ubuntu 24.04 container are available for testing the setup
in a clean environment without touching your host.

```bash
# Run server setup in a Fedora container
bash docker-run.sh -d fedora -t server

# Run slim setup in an Ubuntu container
bash docker-run.sh -d ubuntu -t slim

# Run full setup in a Fedora container
bash docker-run.sh -d fedora -t full
```

`docker-run.sh` starts the selected container, runs `setup.sh` with the chosen
profile, and then drops you into a shell inside the configured environment.

Equivalent manual commands inside the container:

```bash
bash /home/devuser/code/dotfiles/setup.sh --server
bash /home/devuser/code/dotfiles/setup.sh --slim --update
bash /home/devuser/code/dotfiles/setup.sh --full --update
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

See `docs/setup_wsl.md` for WSL2-specific setup notes and workarounds.
