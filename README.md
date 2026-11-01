# dotfiles

A personal development environment built with Bash and GNU Stow: shell,
terminal, editor, CLI tools, and an optional Hyprland desktop.

Supports Arch Linux, Fedora 42+, and Ubuntu 24.04+, on native Linux and WSL2.
Hyprland is native Arch only.

## Installation

Start with an installed OS, networking, Git, and sudo access. Desktop hardware
support (graphics, audio, Bluetooth) should already be configured.

```bash
git clone <repo-url> ~/.dotfiles
cd ~/.dotfiles
bash setup.sh --full
```

Choose a profile:

| Profile | Includes |
|---|---|
| `--server` | Bash, Vim, tmux, and minimal operational tools |
| `--slim` (default) | Workstation dotfiles, Zsh, Oh My Zsh, and common tools |
| `--full` | Slim + mise-managed development tools, Neovim, Node, and Python utilities |

Add `--hyprland` to slim/full for the Arch desktop, or `--update` to upgrade
system packages first on Arch/Fedora. Full native Fedora also installs
container tooling.

Restart the shell with `exec zsh -l` (`exec bash -l` for servers).
With `--hyprland`, the desktop starts on the next local tty1 login; see the
[Hyprland guide](docs/setup_hyprland.md) for desktop setup and customization.

## What's included

| Stow packages | Contents |
|---|---|
| `zshrc`, `zprofile` | Zsh, completion, shell helpers, and login environment |
| `tmux` | Terminal multiplexer with editor navigation |
| `nvim` | Neovim with completion, LSP, Git indicators, highlighting, and search |
| `mise` | Node, Neovim, Bat, eza, Tealdeer, Lazygit, fastfetch, ripgrep, fd, and fzf |
| `tealdeer` | System trust store for tldr downloads |
| `themes` | Everforest and Gruvbox across terminal, editor, and desktop |
| `opencode`, `claude` | AI coding-tool configuration |
| `espanso` | Text expansion |
| `foot`, `hypr`, `waybar`, `wofi`, `mako` | Optional Hyprland desktop |
| `bashrc-server`, `vim-server`, `tmux-server` | Minimal headless configuration |
| `gtk` | Optional settings for an externally installed GTK theme |

## Managing dotfiles

Directories under `packages/` mirror paths below `$HOME`. Setup links the
selected packages; use these commands from the repository root to manage links:

| Command | Action |
|---|---|
| `make stow` / `make restow` | Link workstation packages |
| `make stow-server` | Link server packages |
| `make stow-hyprland` | Link workstation and desktop packages |
| `make stow-foot` | Link Foot and shared themes |
| `make stow-gtk` | Link GTK settings |

These commands only link configuration, not install software. Corresponding
`unstow` targets unlink their group; `make unstow` leaves desktop links alone.

Stow stops on conflicts: preserve local files rather than overwriting them or
using `--adopt`. Optionally preview an individual package with
`stow --simulate --no-folding --dir=packages --target="$HOME" <package>`.

## Local customization

Keep machine-specific settings in ordinary, untracked files:

| File | Purpose |
|---|---|
| `~/.zshrc.private` | Environment variables and shell overrides |
| `~/.config/mise/config.local.toml` | Tool versions and extra tools |
| `~/.config/nvim/local.lua` | Language servers, parsers, and editor features |
| `~/.config/tmx/init.zsh` | Layout and startup commands for new tmux sessions |
| `~/.config/hypr/hyprland.lua` | Desktop entrypoint and monitor/hardware overrides |

Config paths respect `XDG_CONFIG_HOME`. Do not Stow or commit these local files.
Restart the relevant application after editing.

For example, to follow Node LTS on one machine, put this in the local mise file:

```toml
[tools]
node = "lts"
```

## Everyday use

### Tools

The full profile installs the tools declared in
[`config.toml`](packages/mise/.config/mise/config.toml). Updates are explicit:

```bash
cd "$HOME"
mise install              # install configured tools
mise outdated             # inspect available updates
mise upgrade --no-prune    # update while retaining installed versions
```

Edit shared tool choices in the repository or use the local override above,
rather than commands that rewrite the Stow-managed global config. Project
`.nvmrc` and `.node-version` files take precedence over global Node settings.

### Sessions

```bash
tmx                         # list sessions
tmx project                 # attach/switch, or create in the current directory
tmx project ~/code/project   # choose the directory for a new session
tmx -h                      # help
```

The tmux prefix is **Ctrl+s**. New windows and splits inherit the active pane's
directory. Session layout customization belongs in the local hook above.

### Themes

Everforest is the default. Switch the shared theme with:

```bash
theme-set gruvbox
theme-set everforest
theme-set                   # show current selection
```

### Neovim

Requires Neovim 0.12+. Plugins install on first launch with Git/network access.
TypeScript/JavaScript, CSS, YAML, and Bash LSP support is configured; install
the language servers and parsers you want explicitly:

```vim
:Mason
:InstallParsers
```

Parser builds require standalone tree-sitter CLI 0.26.1+, a C compiler, curl,
and tar. Formatting, ESLint diagnostics, and Markdown preview are opt-in through
`local.lua`; formatting and linting use only the project's own dependencies.
See [`settings.lua`](packages/nvim/.config/nvim/lua/config/settings.lua) for
available settings. Press Space for keybinding hints.

## Checks

```bash
make check
python3 scripts/prepare-test-fixtures.py /absolute/path/to/empty-fixture-directory
make check-runtime FIXTURES=/absolute/path/to/empty-fixture-directory
```

Fixture preparation downloads dependencies; runtime checks use disposable homes.
Prerequisites and component-specific commands are in the
[maintainer reference](AGENTS.md#testing).

## Further details

- [Arch Hyprland setup](docs/setup_hyprland.md)
- [WSL2 setup](docs/setup_wsl.md)
- [Maintainer reference](AGENTS.md)
