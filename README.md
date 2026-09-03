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
| `bob` | Bob Neovim version-manager configuration and runtime paths |
| `foot` | Default Foot terminal configuration (zsh shell, switchable palette) |
| `themes` | Gruvbox and Everforest packs (Foot, tmux, Neovim, Waybar, Hyprland, Wofi, Mako, swaybg fallback, wallpaper) plus `theme-set`, `foot-reload`, and `swaybg-current` |
| `gtk` | Opt-in GTK3/GTK4 settings and libadwaita imports for the external Everforest theme |
| `hypr` | Hyprland Lua configuration (keybindings, theme-driven styling, wallpaper, idle policy, clipboard history, `hyprland-session.target`, and `swaybg.service`) |
| `waybar` | Switchable Waybar status bar (Hyprland workspaces, window title, audio, network, tray, clock) |
| `wofi` | Wofi application launcher (compact layout, theme-driven palette) |
| `mako` | Mako notifications (theme-driven colors, urgency states, compact geometry) |
| `opencode` | OpenCode AI and TUI config (commands, agents, models, watcher settings) |
| `claude` | Claude Code permissions, hooks, and MCP configuration |
| `espanso` | Espanso text expansion configuration |

## Prerequisites

- Arch Linux, Fedora 42+, or Ubuntu 22.04+
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

The Hyprland session uses `swaybg` to load the selected theme's wallpaper,
`~/Pictures/Wallpapers/<theme>.<ext>` where `<ext>` is `.png`, `.jpg`, or
`.jpeg` (for example `everforest.png` or `gruvbox.jpg`), in fill mode. The
image stays local rather than being redistributed through this public
repository. If it is absent, `swaybg` uses the fallback color of the selected
theme instead.

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
| `--slim` | curl, fastfetch, gh, git, gcc, make, stow, tmux, zsh, Oh My Zsh, zsh-autosuggestions, dotfiles |
| `--full` | Everything in slim + Podman + Docker-compatible CLI on native Fedora, eza, fzf, ripgrep, bat, htop, native Neovim on Arch/Fedora, Bob stable Neovim on Ubuntu/Debian, nvm, node LTS, uv, tldr, llm |

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

Stow packages are stored under `packages/`; their contents still mirror the
paths expected below `$HOME`.

| Target | Description |
|---|---|
| `make stow` | Symlink the default workstation packages to `$HOME` |
| `make stow-server` | Symlink only the server profile dotfiles to `$HOME` |
| `make stow-gtk` | Symlink the opt-in Everforest GTK settings after installing the external theme |
| `make stow-foot` | Symlink the Foot configuration and shared theme assets to `$HOME` |
| `make unstow` | Remove the default workstation package symlinks |
| `make unstow-server` | Remove only the server profile symlinks |
| `make unstow-gtk` | Remove only the Everforest GTK settings symlinks |
| `make unstow-foot` | Remove only the Foot configuration, retaining shared theme assets |
| `make restow` | Ensure default workstation package links exist after adding files without removing live configuration |

## Theme switching

Everforest is selected automatically the first time the workstation packages
are stowed. Switch all supported applications with one command:

```bash
theme-set gruvbox
theme-set everforest
theme-set            # prints the active theme
```

A theme pack contains a native fragment per supported component: `foot.ini`,
`tmux.conf`, `nvim.lua`, `waybar.css`, `hyprland.lua`, `wofi.css`, `mako.conf`,
`swaybg-color`, and `wallpaper-name`. Fragments are generated from one semantic
palette per theme
(`scripts/palettes/*.json`) with `make themes-generate`; `make themes-check`
verifies the checked-in fragments are current. The command validates the pack
before switching and replaces the `current` symlink atomically; invalid or
incomplete packs never change the selection.

The command updates tmux, Waybar, Mako, and Hyprland immediately, starts a
replacement `swaybg` instance before stopping the previous one to switch the
background without a blank frame, and repaints running
Foot terminals via OSC color updates. Each reload is
independent and best-effort: a missing application or failed reload warns
without reverting the selection. Wofi and new Foot instances pick up the theme
when launched, and running Neovim instances re-apply it with `:ReloadTheme` or
automatically on focus.
Static theme packs live under
`~/.local/share/dotfiles/themes`, while the local `current` symlink lives under
`~/.local/state/dotfiles/theme` so switching themes does not modify the Git
worktree.

## Docker testing

A Fedora, Ubuntu 24.04, and Arch container are available for testing the setup
in a clean environment without touching your host.

```bash
# Run server setup in a Fedora container
bash docker/run.sh -d fedora -t server

# Run slim setup in an Ubuntu container
bash docker/run.sh -d ubuntu -t slim

# Run full setup in a Fedora container
bash docker/run.sh -d fedora -t full

# Run server setup in an Arch container
bash docker/run.sh -d arch -t server
```

`docker/run.sh` starts the selected container, runs `setup.sh` with the chosen
profile, and then drops you into a shell inside the configured environment.

Use `docker/test.sh` to recreate a selected container, run a profile twice, and
assert its commands, login shell, and Stow links:

```bash
bash docker/test.sh -d arch -p server
```

Equivalent manual commands inside the container:

```bash
bash /home/devuser/code/dotfiles/setup.sh --server
bash /home/devuser/code/dotfiles/setup.sh --slim --update
bash /home/devuser/code/dotfiles/setup.sh --full --update
```

### Docker reference

```bash
# Connect to a running container
docker compose -f docker/compose.yml exec dotfiles-fedora bash
docker compose -f docker/compose.yml exec dotfiles-ubuntu bash
docker compose -f docker/compose.yml exec dotfiles-arch bash

# Stop and remove containers
docker compose -f docker/compose.yml down

# Remove images
docker rmi auek/dotfiles:fedora
docker rmi auek/dotfiles:ubuntu
docker rmi auek/dotfiles:arch
```

See `docs/setup_wsl.md` for WSL2-specific setup notes and workarounds.
