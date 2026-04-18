# Archived Implementation Plan: `--server` profile

Status: done. The `--server` profile has been implemented and this plan is kept
for historical reference.

## Goal

Replace the old `--tiny` concept with a `--server` profile in `setup.sh` for
remote/headless servers accessed primarily over SSH. The focus is conservative,
operationally useful tooling with minimal shell customization and no workstation
or AI-specific workflow assumptions.

This plan is intended to align with the guidance in
`/home/august/vaults/main/wiki/references/server-tooling-conventions.md`:

- keep the profile Bash-first
- keep the package set small and justified
- prefer lightweight SSH ergonomics over personal workstation preferences
- exclude tools that are mainly for development workflows rather than server
  operation

## Profile hierarchy

```
server  ⊂  slim  ⊂  full
```

## What `--server` installs

| Category | Packages |
|---|---|
| Common (both distros) | `curl git make stow tmux vim` |
| Optional | nothing |
| Dev tools | nothing |
| Shell change | none |
| OMZ / zsh plugins | skipped |

## What `--server` stows

| Package | Included |
|---|---|
| `bashrc-server` | yes |
| `tmux-server` | yes |
| `zshrc` | no |
| `zprofile` | no |
| `nvim` | no |
| `kitty` | no |
| `opencode` | no |
| `claude` | no |
| `espanso` | no |

The intent is to keep `--server` intentionally boring and host-native.

---

## Changes required

### 1. Add `bashrc-server/.bashrc`

Create a dedicated minimal Bash config for server environments instead of trying
to make the workstation `.zshrc` degrade gracefully.

This file should extract only the parts of the current `zshrc/.zshrc` that are
useful on remote/headless systems.

#### Include

- history settings for large persistent history
- `bind 'set bell-style none'`
- `bind 'set completion-ignore-case on'`
- basic aliases:
  - `p='pwd'`
  - `..='cd ..'`
  - `...='cd ../..'`
  - `....='cd ../../../..'`
- small git aliases:
  - `gst='git status'`
  - `gb='git branch'`
  - `glg='git log'`

#### Exclude

- any `zsh`-specific settings
- OMZ and plugin logic
- `with_secrets()`
- `dev()`
- `gsuggest()`
- `llm`, `opencode`, `claude`
- `fzf` integration
- `eza` aliases
- `nvim` aliasing
- WSL/desktop clipboard helpers
- automatic `ssh-agent` startup

Suggested contents:

```bash
HISTFILE="$HOME/.bash_history"
HISTSIZE=500000
HISTFILESIZE=500000
shopt -s histappend

bind 'set bell-style none'
bind 'set completion-ignore-case on'

alias p='pwd'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../../..'

alias gst='git status'
alias gb='git branch'
alias glg='git log'
```

### 2. Add `tmux-server/.tmux.conf`

Create a server-specific tmux config derived from the current `tmux/.tmux.conf`.
Reuse most of the existing tmux behavior, but remove assumptions that are not a
good fit for headless servers.

Use `C-b` for the server prefix so nested local/remote tmux sessions remain
easy to reason about when the workstation profile uses `C-s`.

#### Keep

- prefix remap
- mouse mode
- low `escape-time`
- vi mode
- pane navigation bindings
- window navigation bindings
- synchronize-panes helper
- choose-tree helper
- `update-environment`
- general color/statusline layout

#### Remove or change

- remove clipboard bindings that assume `wl-copy` / `wl-paste`
- remove Darwin/Wayland clipboard branching
- remove hardcoded `default-shell /usr/bin/zsh`
- remove hardcoded `default-command "/usr/bin/zsh -l"`
- consider removing `xterm-kitty:RGB` if maximum portability is preferred, but
  it can stay if it is harmless in practice

The goal is "current tmux style, minus server-hostile assumptions", not a fully
new tmux experience.

### 3. `setup.sh` — replace `--tiny` with `--server`

#### 3a. Argument parsing

Add `--server` as a valid argument:

```bash
--server) PROFILE="server" ;;
```

Update the usage text to:

```bash
Usage: $0 [--server | --slim | --full] [--update]
```

Do not add `--tiny` alongside it unless backward compatibility is explicitly
needed.

#### 3b. Package lists

Add `PKG_SERVER` alongside the existing package groups for each distro:

```bash
# Fedora
PKG_SERVER="curl git make tmux vim"

# Ubuntu/Debian
PKG_SERVER="curl git make tmux vim"
```

#### 3c. Step 2 — Install packages

Add a `server` branch so `--server` installs only the server package set.

#### 3d. Step 5 — Set default shell

Skip this step entirely for `--server`.

Server installs should not install `zsh`, modify `/etc/shells`, or call `chsh`.

#### 3e. Step 7 — Stow dotfiles

Add a `server` branch that stows only the server-specific packages:

```bash
if [ "$PROFILE" = "server" ]; then
  make -C "$REPO_DIR" stow-server
else
  make -C "$REPO_DIR" stow
fi
```

#### 3f. Steps to skip for `--server`

Skip the following entirely when `PROFILE=server`:

- GNOME keybindings
- Oh My Zsh install
- zsh-autosuggestions install
- any full-only dev tool installation

### 4. `Makefile` — add `stow-server` target

Add server-specific package targets:

```makefile
STOW_PACKAGES_SERVER = bashrc-server tmux-server

stow-server:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)

unstow-server:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_SERVER)
```

Update `.PHONY` to include `stow-server` and `unstow-server`.

### 5. `AGENTS.md` — update `setup.sh` design principles

Update the single entrypoint line:

```bash
bash setup.sh [--server | --slim | --full]
```

Add a note under design principles that `--server` is Bash-first and intended
for remote/headless systems.

### 6. `README.md` — update profiles table

Update the profiles table to include:

```markdown
| Flag | What it installs |
|---|---|
| `--server` | curl, git, make, tmux, vim, minimal Bash config, minimal tmux config |
| `--slim` | curl, gh, git, gcc, make, stow, tmux, zsh, Oh My Zsh, zsh-autosuggestions, dotfiles |
| `--full` | Everything in slim + kitty 0.46.2 from upstream + JetBrains Mono (non-WSL), Podman + Docker-compatible CLI on native Fedora, eza, fzf, ripgrep, bat, htop, bob-nvim (stable), nvm, node LTS, uv, tldr, llm |
```

---

## Testing protocol

1. Wipe the container: `docker compose down`
2. Drop into a fresh Fedora container: `bash docker-run.sh -d fedora`
3. Run server install: `bash /home/devuser/code/dotfiles/setup.sh --server`
4. Verify:
   - `bash` remains the login shell unless the container already differs
   - `vim` opens
   - `tmux` starts
   - `.bashrc` loads without errors
   - `bind -V | grep bell-style` shows `none`
   - basic aliases work: `..`, `gst`
   - `zsh` is not required
   - OMZ is not installed
   - `nvim` is not installed
5. Run `setup.sh --server` a second time to verify idempotency

## Notes

- `--server` is for remote/headless systems, not generic "small machines".
- Using Bash is intentional because it matches the default reality on many
  servers and avoids changing the user's login shell.
- The server tmux config should preserve familiar behavior while dropping GUI or
  workstation-specific integrations.
- The server tooling reference should remain the rationale document; this plan
  should stay implementation-focused.
