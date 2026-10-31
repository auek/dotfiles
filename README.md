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
| `mise` | Default Node 24.19.0 and stable Neovim, Bat, eza, Tealdeer, Lazygit, fastfetch, ripgrep, fd, and fzf |
| `tealdeer` | Use the system certificate trust store for tldr page downloads |
| `zshrc`, `zprofile` | Shell configuration, portable `tmx` sessions with optional local hooks, and login environment |
| `tmux` | Terminal multiplexer with shared editor navigation and current-directory inheritance |
| `nvim` | Shared editor with completion, Git indicators, Treesitter, navigation, and optional local features |
| `bob` | Optional legacy Bob configuration, retained for rollback |
| `themes` | Everforest and Gruvbox theme packs and switching utilities |
| `opencode`, `claude` | AI coding-tool configuration |
| `espanso` | Text expansion configuration |
| `foot`, `hypr`, `waybar`, `wofi`, `mako` | Opt-in Hyprland desktop, terminal, bar, launcher, and notifications |
| `bashrc-server`, `vim-server`, `tmux-server` | Minimal server configuration |
| `gtk` | Separately opt-in settings for the external Everforest GTK theme |

## Development tools with mise

The `--full` profile installs mise and the tools declared in
`packages/mise/.config/mise/config.toml`. Node defaults to the pin `24.19.0`;
the other tools use `latest`, which excludes prereleases by default with the
selected Aqua backends. Updates are explicit:

```zsh
cd "$HOME"
mise install               # install missing configured versions
mise outdated              # inspect available updates
mise upgrade --no-prune     # update within configured versions; retain old versions
```

Do not use `mise use --global`, `mise settings`, or `mise upgrade --bump` to
change configuration: those commands can rewrite the Stow-managed file.
Edit its repository source instead. Project `.nvmrc` and `.node-version`
files override the global Node pin. Existing global npm packages are not
copied between Node installations; reinstall the ones you need locally.
For example, a new Node major may no longer bundle Corepack. Restore it and
any previously enabled package-manager launchers in the active mise Node,
then run `mise reshim`. Verify from a fresh shell without inherited nvm PATH
entries, which can otherwise hide missing commands.

For machine-specific overrides or extra tools, create an ordinary, untracked
`~/.config/mise/config.local.toml` alongside the shared symlink:

```toml
[tools]
node = "lts"
"aqua:astral-sh/uv" = "latest"
```

This follows the current LTS line and adds uv/uvx only on that machine, while
retaining the rest of the shared toolset. Omit the uv entry if it is not needed;
`setup.sh --full` no longer installs uv separately. Set Node to `"latest"`
instead to follow the newest stable release, including non-LTS releases.
Use current mise (2026.8.5+ fixes global override precedence).
The local file overrides the shared global config; project `.nvmrc` and
`.node-version` files still take precedence. Updates remain explicit through
`mise upgrade --no-prune`. Never Stow or commit the machine-local file.

Mise activates in interactive Zsh; shims also support the first command in a
shell and inherited subprocess PATHs. Login shells expose shims without the
interactive hooks. A non-interactive, non-login Zsh inherits its parent's
PATH; scripts launched from other environments can use `mise exec -- command`.
Neovim uses the same upstream release archives as a manual installation.
The current Linux x86_64 0.12.6 build requires glibc 2.34; future stable builds
still need checking on older distributions.

On an existing machine with mise installed, run from the repository root:

**On a limited RHEL/WSL machine, use this targeted workflow. Do not
run `setup.sh` with any profile, including `--full`; RHEL is unsupported.**

```zsh
git switch main
git pull --ff-only
stow --simulate --verbose --restow --no-folding --dir=packages --target="$HOME" mise tealdeer zshrc zprofile
stow --restow --no-folding --dir=packages --target="$HOME" mise tealdeer zshrc zprofile
(cd "$HOME" && mise install && mise reshim)
exec zsh -l
```

Check local changes before pulling. If Stow reports an existing ordinary
configuration file, compare it with the repository version and preserve your
local settings in a backup before resolving the conflict; do not use `--adopt`
or overwrite it. These commands do not switch your Neovim configuration package.
The workstation's existing system tools remain installed.

Verify `mise ls`, `node --version`, `npm --version`, `nvim --version`, and
`whence -pa node nvim bat tldr lazygit fastfetch rg fd fzf`. Then check Neovim's
Node-backed language servers and run `tldr --update`. Tealdeer uses the system
trust store across deployment targets; proxy variables and additional
certificates remain machine-local. Preserve the existing proxy environment for
downloads; if only `http_proxy` is set, also export `https_proxy="$http_proxy"`.

Existing nvm, Bob, and manual/system binaries remain on disk for rollback.
Remove redundant installations only after checking both machines. Stow, tmux,
htop, and shell frameworks keep their existing installers; Python applications
such as llm remain outside mise. uv is an optional machine-local mise tool,
not part of the shared baseline. ShellCheck is an explicit editor-tool install;
shfmt is not part of the shared toolset.

Targeted migration is verified on the Arch workstation with a local Node LTS
override and the existing default `nvim` profile preserved. Shell selection,
project version switching, Tealdeer downloads, and default-profile editor checks
passed; this is not verification of fresh distro provisioning. See the
[migration record](docs/plans/mise-node-migration.md) for scope and measurements.

## Tmux sessions with `tmx`

`tmx` lists, creates, and attaches to tmux sessions. It does not launch an editor
or assistant by default.

```zsh
tmx                         # list sessions (or show a creation hint)
tmx project                 # attach/switch, or create in the current directory
tmx project ~/code/project  # use this directory only when creating
tmx -h                      # show help
```

An existing session is matched by its exact name and left unchanged, even if a
different directory is supplied. Inside tmux, `tmx` switches clients rather than
nesting sessions. Session names cannot contain `.` or `:` or begin with `-` or `$`.

New sessions have one window and one shell pane. To customize them, create an
ordinary, **untracked** `${XDG_CONFIG_HOME:-$HOME/.config}/tmx/init.zsh`. This
machine-local hook runs once per new session in a separate `zsh -ef` process,
before attachment, with four arguments:

1. Session ID (for example, `$1`)
2. Initial window ID (for example, `@1`)
3. Initial pane ID (for example, `%1`)
4. Absolute project directory

For a 50/50 side-by-side split, put this in the local hook:

```zsh
session=$1 window=$2 pane=$3 directory=$4
tmux split-window -d -h -p 50 -t "$pane" -c "$directory"
```

Use `-p 20` instead for an approximately 80/20 layout. The original pane stays
selected. To explicitly start a program there, append, for example:

```zsh
tmux send-keys -t "$pane" -l 'nvim'
tmux send-keys -t "$pane" Enter
```

Choose startup commands explicitly on each machine; installed tools are not
automatically launched. Hooks are trusted shell code, never discovered in a
project, Stowed, or committed. They inherit the caller's environment but do not
load interactive `.zshrc` aliases/functions. A failing command stops the hook
and prints a warning; the session remains accessible and attachment is still
attempted. Reattaching does not retry a failed hook or add panes.

The shared tmux prefix is Ctrl+s. Prefix + `c`, `%`, and `"` create windows or
splits in the active pane's directory. The workstation config declares RGB
support for Foot and `xterm-256color`. After tmux configuration changes, use
`tmux source-file "$HOME/.tmux.conf"`; detach/reattach clients for terminal
feature changes.

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
`make unstow-hyprland` to unlink that group. Legacy `bob` links are also retained.
Linking/unlinking does not clear local state
or the Hyprland autostart preference.

Everforest is selected initially. Switch themes with:

```bash
theme-set gruvbox
theme-set everforest
theme-set            # show current selection
```

## Neovim

The `nvim` package provides one shared editor configuration (Neovim 0.11.3+):
LSP/snippet/path/buffer completion, Git change indicators, Treesitter highlighting,
Telescope search, nvim-tree, a status line, keybinding hints, automatic pairs,
surround editing, and tmux navigation. No assistant completion provider is used.
The optional `themes` package supplies runtime Everforest/Gruvbox selection;
without it the editor defaults to Everforest, with Habamax as the no-plugin fallback.

From the repository root, inspect conflicts before linking:

```bash
stow --simulate --verbose --restow --no-folding --dir=packages --target="$HOME" nvim
stow --restow --no-folding --dir=packages --target="$HOME" nvim
```

Do not overwrite existing ordinary files or use `--adopt`. Restow after pulls
that add/remove configuration files. Plugin bootstrap needs Git/network access;
it fails gracefully to basic editing. Lazy installs missing editor plugins but
does not check for updates on startup. Plugins live in `stdpath("data")/lazy`,
Mason tools in `stdpath("data")/mason`, and Lazy's runtime lockfile/cache/state in
`stdpath("state")/dotfiles`. The tracked `lazy-lock.json` supplies explicit pins;
plugin upgrades are deliberate repository changes. `:Lazy install` reconciles
missing plugins without needing `:Lazy clean` or removing old data.
Project-local `.lazy.lua` plugin specs are disabled.

### Languages and optional features

Available TypeScript/JavaScript (`ts_ls`), CSS/SCSS/Less (`cssls`), YAML/Azure
Pipelines (`yamlls`), and Bash (`bashls`) servers are enabled by default.
**Language servers and parsers are never automatically installed.** With
Node/npm available, explicitly install the tools you need:

```vim
:MasonInstall typescript-language-server css-lsp yaml-language-server bash-language-server shellcheck
:InstallParsers
```

`InstallParsers` installs the selected Bash, CSS, JavaScript, JSON, Lua, TSX,
TypeScript, and YAML parsers. Make/GCC or Clang are needed for native builds;
Telescope's fzf-native sorter also builds with Make. Text search requires `rg`.
If its sorter build fails, Telescope falls back with a warning; retry with
`:Lazy build telescope-fzf-native.nvim`. Nerd Fonts are not required.

Bash's language server uses ShellCheck on PATH for diagnostics. Shell
formatting is disabled; no shfmt is installed or configured as a formatter.
Other available tools can come from Mason or the existing shell environment.
Installing a selected server through Mason also enables it for already-open
buffers. Unselected servers are not enabled just because they are installed.

For machine-specific choices, create an ordinary, **untracked**
`~/.config/nvim/local.lua` (under `XDG_CONFIG_HOME` when set), for example:

```lua
return {
  servers = { pyright = true, cssls = false }, -- add/disable individual LSPs
  -- Optional list replaces the default parser list:
  parsers = { "bash", "css", "javascript", "json", "lua", "python", "tsx", "typescript", "yaml" },
  features = {
    format_on_save = false,
    markdown_preview = false,
  },
  server_options = { lua_ls = { settings = { Lua = { diagnostics = { globals = { "vim" } } } } } },
}
```

Omit unchanged settings. Restart Neovim after changing this file; install any
newly selected servers/parsers explicitly. `server_options` customizes LSP
configurations but does not enable unselected servers. Malformed local settings
produce a warning and fall back to defaults. Never Stow or commit this file.
Format-on-save is off by default; opting in loads Conform with Lua/Python
formatters (installed separately) and LSP fallback, never shell formatting.
Markdown preview is also opt-in and requires an npm build. No dashboard,
custom notification UI, separate Git command interface, or extra diagnostics
window is included.

Azure schema associations cover `azure-pipelines*.yml`/`.yaml` and
`.azure-pipelines/`. For other template paths, use a YAML schema modeline.
The schema is fetched from Microsoft's upstream repository when needed;
SchemaStore auto-discovery is disabled. Existing proxy/CA settings are preserved.
Use `:MasonLog`, `:checkhealth mason`, and `:checkhealth vim.lsp` for troubleshooting.

### Everyday editing

| Key | Action |
|---|---|
| Space f e | Toggle file tree; dotfiles shown, `.git` hidden |
| Space f f / Space f g | Find files / search text, respecting ignores |
| Space f F / Space f G | Find files / search text including ignored paths |
| Space f o / Space l s / Space f h | Recent files / buffers / help |
| Ctrl+f on command line | Search command history |
| Ctrl+h/j/k/l | Move between editor/tmux panes, without saving buffers |
| Ctrl+n/p / Space b | Cycle buffers / safely close a clean buffer |
| Space w / Space q / `jj` | Write / quit / leave insert mode |
| `gd` / `gh` / Space c r / Space c a | Definition / hover / rename / code actions |
| Space d / `[d` / `]d` | Show / previous / next diagnostic |
| Visual Space y / normal Space p | Explicit system clipboard copy / paste |

Searches use the current directory. Space-separated file queries such as
`foo File` match full paths with fzf syntax. `nvim .` and `:edit directory`
open the tree. Completion keeps the existing Tab/Shift-Tab, Enter and
Ctrl+Space bindings; native `gc` commenting is available. Markdown/text wrap.
Theme changes reload on focus or with `:ReloadTheme`. Markdown Treesitter
highlighting remains disabled due to the known Neovim 0.12 crash.
External file changes reload only clean buffers, deferring during insert and
command-line editing. Closing a modified buffer never discards its changes.

On WSL, explicit clipboard operations use PowerShell UTF-8 stdin/output when
available; ordinary yanks/deletes never start a Windows process. Clipboard text
is never executed as code. Native platforms use available Neovim providers.
Real Windows clipboard/Windows Terminal behavior still requires manual checking.

### Existing installations

If a machine uses the old `nvim-work` package, **unstow it from the old checkout
before pulling this change**, then Stow `nvim` using the commands above:

```bash
stow --delete --no-folding --dir=packages --target="$HOME" nvim-work
git pull --ff-only
```

If already pulled, stop on dangling-link conflicts and inspect them rather than
deleting or adopting files automatically. The default package selection stays
`nvim`. Existing plugins, servers and the old profile's data are not removed;
the old profile's separate data is not automatically copied into the shared
locations. Review extra language needs in `local.lua`; broad automatic server
installation and format-on-save are not defaults.

### Isolated checks

```bash
python3 scripts/test-nvim.py /absolute/path/to/nvim
python3 scripts/test-nvim.py /absolute/path/to/nvim /path/to/plugin-fixtures
```

Fixtures contain the repositories in `lazy-lock.json` (fzf-native already built).
Checks copy them into disposable homes, exercise local settings, completion,
Git indicators, parser configuration, search/tree/themes, clipboard and safe
buffer behavior, and verify package removal preserves local settings. An
optional third argument supplies a Mason fixture with the four baseline servers,
ShellCheck and `azure-schema.json` for real LSP/diagnostic checks without downloads.
Tests never install plugins or tools into the real home.

## Further details

- [Arch Hyprland setup and customization](docs/setup_hyprland.md), including
  local hardware overrides, autostart, and migration from the earlier setup.
- [WSL2 setup](docs/setup_wsl.md), including Fedora's separate container setup.
- [Maintainer reference](AGENTS.md): repository structure, theme generation,
  platform conventions, and isolated container testing.
