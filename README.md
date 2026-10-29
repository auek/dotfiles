# dotfiles

A development environment bootstrapped with Bash and GNU Stow. Supports Arch
Linux, Fedora 42+, and Ubuntu 24.04+, on native Linux and WSL2. The optional
Hyprland desktop is supported on native Arch only.

## Installation

Start with an installed OS, working networking, `git`, and sudo access. For an
Arch desktop, configure graphics drivers, audio, Bluetooth, and other hardware
support first; this repository does not provision hardware.

```bash
git clone <repo-url> ~/.dotfiles
cd ~/.dotfiles
bash setup.sh                   # default: slim development environment
bash setup.sh --full            # full development environment
bash setup.sh --full --hyprland # Arch development environment + desktop
bash setup.sh --server          # minimal headless environment
```

Add `--update` to upgrade system packages before installation on Arch/Fedora.
Setup preserves existing local configuration and stops on conflicting Stow
files rather than overwriting them.

| Option | Scope |
|---|---|
| `--server` | Bash, Vim, tmux, and minimal operational tools |
| `--slim` | Workstation dotfiles, Zsh, Oh My Zsh, and common tools (default) |
| `--full` | Slim + development tools, Neovim, Node, Python utilities; container tooling on native Fedora |
| `--hyprland` | Arch desktop packages/configuration and opt-in tty1 autostart; combines with slim or full |

After general setup, restart your shell with `exec zsh -l` (or `exec bash -l`
for servers). With `--hyprland`, the desktop starts on the next local Arch tty1
login; setup does not launch it.

**Hyprland bootstrap verification:** migration on the existing Arch workstation
has been smoke-tested. A fresh install with `setup.sh --hyprland` has not yet
been tested; verification is deferred until the next Arch installation.

## What's included

| Stow packages | Contents |
|---|---|
| `zshrc`, `zprofile` | Shell configuration and login environment |
| `nvim-work` | Opt-in, built-in-only Neovim work profile (alternative to `nvim`) |
| `tmux`, `nvim`, `bob` | Terminal multiplexer, editor, and Neovim version-manager settings |
| `themes` | Everforest and Gruvbox theme packs and switching utilities |
| `opencode`, `claude` | AI coding-tool configuration |
| `espanso` | Text expansion configuration |
| `foot`, `hypr`, `waybar`, `wofi`, `mako` | Opt-in Hyprland desktop, terminal, bar, launcher, and notifications |
| `bashrc-server`, `vim-server`, `tmux-server` | Minimal server configuration |
| `gtk` | Separately opt-in settings for the external Everforest GTK theme |

## Managing dotfiles

Packages live under `packages/`, mirroring paths below `$HOME`.

| Command | Action |
|---|---|
| `make stow` / `make restow` | Link general workstation packages |
| `make stow-hyprland` | Link workstation + desktop packages (no installation or autostart opt-in) |
| `make stow-server` | Link server packages |
| `make stow-foot` | Link Foot and shared themes separately |
| `make stow-gtk` | Link GTK settings after installing the external theme |

Corresponding `unstow` targets remove only their package group's links.
General `make unstow` retains the separate desktop group; use
`make unstow-hyprland` to unlink it. Linking/unlinking does not clear local state
or the Hyprland autostart preference.

Everforest is selected initially. Switch themes with:

```bash
theme-set gruvbox
theme-set everforest
theme-set            # show current selection
```

## Minimal Neovim work profile

With Neovim already installed, `nvim-work` provides an offline editor using
built-in syntax, filetype indentation, and the Habamax colorscheme. It needs
no plugins, theme package, language servers, or additional tools. A small set
of plain options and mappings is copied from the home profile so this package
can stand alone without loading the home plugin bootstrap.

`nvim` and `nvim-work` are alternative profiles targeting `~/.config/nvim`.
**Do not stow both.** Default `make stow` and setup profiles still select the
home `nvim` package. Unstow your previous profile before switching. If Stow
reports existing files, resolve the conflict yourself; do not overwrite,
`--adopt`, or automatically delete them.

From the repository root, activate only this package:

```bash
stow --simulate --verbose --no-folding --dir=packages --target="$HOME" nvim-work
stow --no-folding --dir=packages --target="$HOME" nvim-work
nvim
```

Space is the leader. `jj` leaves insert mode, Ctrl+h/j/k/l moves between
windows, Ctrl+n/p cycles buffers, and leader+w/q writes/quits. Leader+b closes
a clean buffer while retaining splits; modified buffers must be saved first.
`:W`, `:Wq`, and `:WQ` are also available. Markdown and text buffers wrap.
External edits reload unmodified buffers on focus, buffer entry, or idle;
checks defer during insert/command-line editing and never overwrite unsaved
changes. This does not change the home profile's reload implementation.

Visual leader+y copies to the system clipboard; normal leader+p pastes.
On WSL, if `powershell.exe` is available, both `*` and `+` use the Windows
clipboard with UTF-8 stdin/output. Clipboard text never becomes PowerShell
code. PowerShell runs only for explicit clipboard operations; ordinary
editing uses normal registers. Otherwise Neovim can use its native clipboard
providers when available. No clipboard utility is installed by this package.

On the actual Windows/WSL machine, verify normal `nvim` startup, split/buffer
keys, copying and pasting multiline text with `åäö`, quotes and backslashes,
an empty clipboard, and Windows CRLF text. Confirm external edits reload a
clean buffer while unsaved edits stay intact. Linux mocks cannot validate
Windows clipboard behavior or interactive Windows Terminal/tmux behavior.

Remove only this profile with:

```bash
stow --delete --no-folding --dir=packages --target="$HOME" nvim-work
```

After this change is merged into your tracked branch, `git pull --ff-only`
will include it. Pulling before merge does not install the unmerged PR.
For isolated developer checks (Neovim and Stow must already be on PATH):

```bash
python3 scripts/test-nvim-work.py /absolute/path/to/nvim
```

## Further details

- [Arch Hyprland setup and customization](docs/setup_hyprland.md), including
  local hardware overrides, autostart, and migration from the earlier setup.
- [WSL2 setup](docs/setup_wsl.md), including Fedora's separate container setup.
- [Maintainer reference](AGENTS.md): repository structure, theme generation,
  platform conventions, and isolated container testing.
