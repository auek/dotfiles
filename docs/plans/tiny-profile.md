# Feature Implementation Plan: `--tiny` profile

## Goal

Add a `--tiny` profile to `setup.sh` for portable, minimal environments such as
servers, VPS instances, and Raspberry Pi. The focus is on essentials: a good
editor, tmux, and shell aliases/config — with the smallest possible footprint.

## Profile hierarchy

```
tiny  ⊂  slim  ⊂  full
```

## What `--tiny` installs

| Category | Packages |
|---|---|
| Common (both distros) | `curl git make tmux vim zsh` |
| Optional | nothing |
| Dev tools | nothing |
| OMZ | skipped |
| zsh-autosuggestions | skipped |

## What `--tiny` stows

| Package | Included |
|---|---|
| `zshrc` | yes |
| `tmux` | yes |
| `zprofile` | no — PATH additions (bob/nvim-bin, NVM) are irrelevant without those tools |
| `nvim` | no |
| `aider` | no |

---

## Changes required

### 1. `zshrc/.zshrc` — wrap OMZ block in a guard

The OMZ configuration block (theme, plugins, zstyle, source) must be wrapped
in a directory existence check so `.zshrc` degrades gracefully when OMZ is not
installed.

**Current (lines 16–24):**
```zsh
### Oh My Zsh Configuration ###
ZSH_THEME="robbyrussell"
plugins=(git ssh-agent zsh-autosuggestions)

# OMZ Plugin Settings
zstyle ':omz:*' aliases no
zstyle :omz:plugins:ssh-agent identities id_ed25519

source $ZSH/oh-my-zsh.sh
```

**Replace with:**
```zsh
### Oh My Zsh Configuration ###
if [ -d "$ZSH" ]; then
  ZSH_THEME="robbyrussell"
  plugins=(git ssh-agent zsh-autosuggestions)
  zstyle ':omz:*' aliases no
  zstyle :omz:plugins:ssh-agent identities id_ed25519
  source "$ZSH/oh-my-zsh.sh"
fi
```

Note: all other aliases and tool integrations in `.zshrc` are already guarded
with `command -v` checks — no further changes needed there.

---

### 2. `setup.sh` — add `--tiny` profile

#### 2a. Argument parsing
Add `--tiny` as a valid argument:
```bash
--tiny) PROFILE="tiny" ;;
```

Update the usage error message to include `--tiny`.

#### 2b. Package lists (Step 1, OS detection block)
Add `PKG_TINY` alongside `PKG_COMMON` and `PKG_OPTIONAL` for each distro:

```bash
# Fedora
PKG_TINY="curl git make tmux vim zsh"

# Ubuntu/Debian
PKG_TINY="curl git make tmux vim zsh"
```

Both distros use the same package names here — identical lists.

#### 2c. Step 2 — Install packages
Add a `tiny` branch:
```bash
if [ "$PROFILE" = "tiny" ]; then
  $PKG_INSTALL $PKG_TINY
elif ...(existing slim/full logic)
```

#### 2d. Step 4 — Set default shell
Make `chsh` non-fatal on `--tiny` since server environments may restrict it:
```bash
sudo chsh -s "$ZSH_PATH" "$USER" || warning "Could not set default shell — set it manually with: chsh -s $ZSH_PATH"
```

Apply this change for all profiles (it's a safe improvement regardless).

#### 2e. Step 6 — Stow dotfiles
Add a `tiny` branch that stows only `tmux` and `zshrc`:
```bash
if [ "$PROFILE" = "tiny" ]; then
  make -C "$REPO_DIR" stow-tiny
else
  make -C "$REPO_DIR" stow
fi
```

#### 2f. Steps 7, 8, 9 — Skip entirely for `--tiny`
Wrap each step with a profile check:
```bash
if [ "$PROFILE" != "tiny" ]; then
  # ... OMZ install
fi
```

```bash
if [ "$PROFILE" != "tiny" ]; then
  # ... zsh-autosuggestions install
fi
```

Step 9 (dev tools) is already gated on `[ "$PROFILE" = "full" ]` — no change needed.

---

### 3. `Makefile` — add `stow-tiny` target

```makefile
STOW_PACKAGES_TINY = tmux zshrc

stow-tiny:
	stow --restow --target=$(STOW_TARGET) $(STOW_PACKAGES_TINY)

unstow-tiny:
	stow --delete --target=$(STOW_TARGET) $(STOW_PACKAGES_TINY)
```

Update `.PHONY` to include `stow-tiny` and `unstow-tiny`.

---

### 4. `AGENTS.md` — update `setup.sh` design principles

Add `--tiny` to the single entrypoint line:
```
bash setup.sh [--tiny | --slim | --full]
```

Add a note under design principles:
```
- **Profile hierarchy**: tiny ⊂ slim ⊂ full. --tiny targets servers and
  minimal environments (vim, tmux, zsh aliases only — no OMZ, no dev tools).
```

---

### 5. `README.md` — update profiles table

```markdown
| Flag | What it installs |
|---|---|
| `--tiny` | git, make, tmux, vim, zsh — dotfiles only (zshrc + tmux), no OMZ |
| `--slim` | curl, git, gcc, make, stow, tmux, zsh, Oh My Zsh, zsh-autosuggestions, dotfiles |
| `--full` | Everything in slim + exa, fzf, ripgrep, bat, htop, bob-nvim (stable), nvm, node LTS, tldr |
```

---

## Testing protocol

1. Wipe the container: `docker compose down`
2. Drop into a fresh Fedora container: `bash docker-run.sh -d fedora`
3. Run tiny install: `bash /home/devuser/code/dotfiles/setup.sh --tiny`
4. Verify:
   - `vim` opens
   - `tmux` starts
   - Shell aliases work (e.g. `..`, `gst`)
   - OMZ is NOT installed (`ls ~/.oh-my-zsh` should fail)
   - `nvim` is NOT installed
   - `.zshrc` loads without errors despite OMZ being absent
5. Run `setup.sh --tiny` a second time to verify idempotency

## Notes

- ARM support (Raspberry Pi) is not a concern for this implementation — the
  package lists use distro packages only, no cargo/rustup involved in `--tiny`.
- The `vim` alias in `.zshrc` (`alias vim="nvim"`) is already guarded with
  `command -v nvim` — it will simply not be set on `--tiny`, which is correct.
- `chsh` non-fatal change (step 2d) is a safe improvement for all profiles,
  not just `--tiny`.
