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
| `nvim-work` | Opt-in minimal Neovim profile with Telescope, nvim-tree, and selected theme |
| `tmux`, `nvim` | Terminal multiplexer and default editor configuration |
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
not part of the shared baseline. ShellCheck and shfmt are not added in this migration.

Targeted migration is verified on the Arch workstation with a local Node LTS
override and the existing default `nvim` profile preserved. Shell selection,
project version switching, Tealdeer downloads, and default-profile editor checks
passed; this is not verification of fresh distro provisioning. See the
[migration record](docs/plans/mise-node-migration.md) for scope and measurements.

## Tmux sessions with `tmx`

`tmx` replaces `dev`; it never launches an editor or assistant by default.

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

## Minimal Neovim profile

`nvim-work` uses built-in syntax and filetype indentation, Lazy/Telescope
navigation, nvim-tree, and the existing Everforest/Gruvbox theme selection. A small set of
plain options and mappings is copied from the default profile so this package
stands alone without loading the default plugin collection. The `themes` Stow
package is optional; without a saved selection the editor uses Everforest.
Mason manages explicitly installed language servers. This profile adds no
completion framework or format-on-save. Telescope's fzf-native sorter builds
locally with Make and GCC/Clang.
First launch needs Git and network access to bootstrap Lazy and install plugins.
Once installed, the editor works offline.

`nvim` and `nvim-work` are alternative profiles targeting `~/.config/nvim`.
**Do not stow both.** Default `make stow` and setup profiles still select the
default `nvim` package. Unstow your previous profile before switching. If Stow
reports existing files, resolve the conflict yourself; do not overwrite,
`--adopt`, or automatically delete them.

From the repository root, activate only this package:

```bash
stow --simulate --verbose --no-folding --dir=packages --target="$HOME" nvim-work
stow --no-folding --dir=packages --target="$HOME" nvim-work
nvim
```

After first activation (or after pulling new package files), restow this
package to link its Lua module, then start Neovim:

```bash
stow --restow --no-folding --dir=packages --target="$HOME" nvim-work
nvim
```

Lazy bootstraps on first launch and installs the missing plugins. Use the
standard `:Lazy` interface afterward (`I` installs, `S` syncs). The ten
repositories are pinned: Lazy, Telescope 0.1.8, Plenary, telescope-fzf-native,
vim-tmux-navigator, nvim-tree, Everforest, Gruvbox, Mason, and nvim-lspconfig. Installation
requires Git and GitHub access through your existing network configuration;
it installs no OS packages. Plugins live under
`stdpath("data")/nvim-work/lazy`; the lockfile, package cache, and Lazy state
live under `stdpath("state")/nvim-work`, separate from the default profile and
outside the Stow checkout. Project-local `.lazy.lua` specs are disabled.
Telescope loads only when a picker is used; nvim-tree loads when opening a
directory or using its command/keybinding. Startup checks for missing
plugins but does not check for updates. If bootstrap fails, basic editing
remains available; fix Git/network access and restart Neovim to retry.

| Key | Navigation |
|---|---|
| Space f e | Toggle nvim-tree and reveal the current file |
| Space f f | Find project files, including dotfiles, respecting ignores |
| Space f g | Search project text with ripgrep (`rg`) |
| Space f o | Recent files |
| Space l s | Open buffers |
| Space f h | Help tags |

Pickers use the current working directory; start `nvim` from the project root
or use `:cd`. Telescope uses the standard fzf-native extension for file and
generic sorting. Space-separated terms match the full path, e.g. `foo File`
or `foo long path to`; terms can appear in either order. Smart case means a
lowercase term ignores case while a term containing capitals respects case.
fzf query operators such as `!`, `'`, `^`, `$`, and `|` are supported.
Space f f searches paths; Space f g searches file contents. File finding uses
an available `rg`, `fd`, or standard `find`. Text search requires `rg` on PATH
and reports a clear message if it is missing.

Lazy runs `make` to build fzf-native on installation/updates. Make and GCC or
Clang must already be available; no separate `fzf` executable is needed.
If the build fails, use `:Lazy build telescope-fzf-native.nvim` after resolving
the compiler issue. A warning is shown and Telescope's default sorter remains
available. Node/npm are required for the language servers below. Nerd Fonts
are optional.

Ctrl+h/j/k/l uses the same `vim-tmux-navigator` plugin as the default profile:
it moves between Neovim splits and crosses into tmux panes at editor edges.
Outside tmux it still navigates Neovim splits. The `tmux` and `tmux-server`
packages already contain the matching bindings; no tmux config changes are
needed. If the active tmux session predates those bindings, reload its config
with `tmux source-file "$HOME/.tmux.conf"`. Navigation never automatically
saves modified buffers. Ctrl+\ toggles the previous pane/window through the
plugin's default mapping.

The workstation tmux config declares RGB support for Foot and `xterm-256color`
(used by Windows Terminal), keeping Neovim's background colors accurate.
After changing terminal features, detach and reattach existing tmux clients.

In both tmux profiles, prefix + `c` (new window), `%` (side-by-side split), and
`"` (stacked split) start in the active pane's current directory. The prefix
is Ctrl+s. Reload an existing server with `tmux source-file "$HOME/.tmux.conf"`
after pulling binding changes. Direct `tmux new-window` / `split-window`
commands still need `-c` when a particular working directory is wanted.

The file tree shows dotfiles but hides `.git`. Its optional icon dependency
and Git integration are disabled, keeping this step focused on navigation.
`nvim .`, `nvim /path/to/directory`, and `:edit directory` open nvim-tree.
Netrw is disabled for this profile; ordinary file startup keeps nvim-tree lazy.

Colors follow `theme-set` via
`~/.local/state/dotfiles/theme/current/nvim.lua`, using the same dark, hard
Everforest palette and non-italic settings as the default profile. Existing
`theme-set everforest` / `theme-set gruvbox` commands switch the selection;
Neovim reloads it on focus, buffer entry, or idle. `:ReloadTheme` applies it
immediately. No selection defaults to Everforest; Habamax remains the fallback
when the theme plugins are not installed. The default Neovim config is unchanged.

Language support uses Neovim's built-in LSP with nvim-lspconfig and Mason.
Lazy installs the editor plugins; it does **not** install language servers.
Launch Neovim from a shell where `node` and `npm` work, then use `:Mason`
to install these three packages (or run the standard command below):

```vim
:MasonInstall typescript-language-server css-lsp yaml-language-server
```

| Mason package | LSP name | Scope |
|---|---|---|
| `typescript-language-server` | `ts_ls` | TypeScript, JavaScript, React/TSX |
| `css-lsp` | `cssls` | CSS, SCSS, Less, CSS Modules stylesheet contents |
| `yaml-language-server` | `yamlls` | YAML and Azure Pipelines schemas |

Mason's package installation and executables live under
`stdpath("data")/nvim-work/mason`, separate from the default profile's Mason.
Available servers start on matching files, including files opened before a
Mason installation finishes. Missing servers do not cause startup failures.
No Mason bridge plugin or automatic server installation list is needed.
CSS Modules import navigation and a completion UI are later additions.
Project TypeScript settings come from the project's tsconfig/jsconfig.

In attached buffers: `gd` goes to definition, `gh` shows hover documentation,
`grr` lists references (Neovim's built-in mapping), Space c r renames,
Space c a offers code actions, Space d shows a diagnostic, and `[d` / `]d`
move between diagnostics. No buffer is formatted automatically.

Azure schema matching applies to `azure-pipelines*.yml` / `.yaml` and files
under `.azure-pipelines/`. For templates elsewhere, add a YAML modeline:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/microsoft/azure-pipelines-vscode/master/service-schema.json
```

The Azure schema is fetched when needed from Microsoft's upstream repository;
YAML SchemaStore auto-discovery is disabled. Existing project modelines may
select other schemas. Registry refresh, npm packages, and schema downloads
must be reachable through the existing proxy/trust configuration. If installation
fails, inspect `:MasonLog` and `:checkhealth mason`; `:checkhealth vim.lsp`
shows enabled clients. This configuration does not alter proxy or CA settings.

Space is the leader. `jj` leaves insert mode, Ctrl+h/j/k/l moves between
windows, Ctrl+n/p cycles buffers, and leader+w/q writes/quits. Leader+b closes
a clean buffer while retaining splits; modified buffers must be saved first.
`:W`, `:Wq`, and `:WQ` are also available. Markdown and text buffers wrap.
External edits reload unmodified buffers on focus, buffer entry, or idle;
checks defer during insert/command-line editing and never overwrite unsaved
changes. This does not change the default profile's reload implementation.

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
# Also exercise real Telescope file/text search using pre-fetched, pinned repos:
python3 scripts/test-nvim-work.py /absolute/path/to/nvim /path/to/plugin-fixtures
```

The optional fixture directory must contain `lazy.nvim`, `telescope.nvim`,
`plenary.nvim`, `nvim-tree.lua`, `everforest-nvim`, `gruvbox.nvim`, `mason.nvim`,
`nvim-lspconfig`, `telescope-fzf-native.nvim` (already built), and
`vim-tmux-navigator` at the commits in `lua/work/plugins.lua`; integration checks
copy them into disposable XDG data and require `rg`. Checks never install
plugins into your real home. Real WSL clipboard/terminal behavior remains a
manual check; the reported `åäö` issue is deferred. An optional third argument
supplies a preinstalled Mason fixture (preserve symlinks, and include Microsoft's
`azure-schema.json` at its root) to exercise real TS definition/type diagnostics,
CSS Modules diagnostics, Less attachment, and Azure YAML schema validation.
Those checks copy the fixture and do not install servers into the real home.

## Further details

- [Arch Hyprland setup and customization](docs/setup_hyprland.md), including
  local hardware overrides, autostart, and migration from the earlier setup.
- [WSL2 setup](docs/setup_wsl.md), including Fedora's separate container setup.
- [Maintainer reference](AGENTS.md): repository structure, theme generation,
  platform conventions, and isolated container testing.
