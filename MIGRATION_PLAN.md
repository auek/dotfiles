# Migration Plan: `dotfiles-ansible` → `dotfiles`

## Goal

Remove the Ansible layer entirely. Replace it with a single `setup.sh` bash script + GNU Stow. The repo becomes leaner, easier to understand, and has no external dependencies to bootstrap.

## Context

The current repo uses Ansible purely as a sequenced local installer — no remote orchestration, no inventory, no vaults. GNU Stow already handles the actual dotfile symlinking. Ansible adds overhead without meaningful benefit, and was primarily a learning exercise.

## Approach

Start from a **fresh repo** cloned from this one (to preserve git history as a reference), then strip out the Ansible layer. Do not modify this repo.

---

## New Repo Structure

```
dotfiles/
├── setup.sh                  # Main bootstrap (replaces bin/bootstrap + all ansible roles)
├── Makefile                  # Stow link/unlink (carries over from .dotfiles/makefile)
├── Dockerfile.fedora         # Updated for new structure
├── Dockerfile.ubuntu         # Updated for new structure
├── docker-compose.yml        # Updated mount paths
├── docker-run.sh             # Updated to call setup.sh instead of bootstrap
├── README.md
│
├── zshrc/.zshrc
├── zprofile/.zprofile
├── tmux/.tmux.conf
├── aider/.aider.conf.yml
├── aider/.aider.model.settings.yml
├── nvim/.config/nvim/        # Full neovim config tree
└── scripts/
    └── tmux-panes.sh
```

No `.dotfiles/` subdirectory — dotfiles live at the repo root (the standard stow layout).

---

## `setup.sh` Design

```
setup.sh [--slim | --full]   # default: --slim
```

### Steps (in order)

1. **Detect OS** — support Fedora (dnf) and Ubuntu/Debian (apt). Fail with a clear message on unsupported distros.
2. **Install common packages** (slim + full):
   `curl git make pipx python3 stow tmux unzip zsh`
3. **Install optional packages** (full only, best-effort — non-fatal on failure):
   `exa fd-find fzf htop bat ripgrep openssh-client`
4. **Set zsh as default shell** — `chsh -s $(which zsh) $USER` (no hardcoded username)
5. **Symlink repo** — ensure `~/.dotfiles` symlinks to the repo directory
6. **Stow dotfiles** — run `make` (or call stow directly)
7. **Install Oh My Zsh** — curl installer, `--unattended --keep-zshrc`
8. **Install zsh-autosuggestions** — git clone into OMZ custom plugins, pinned to v0.7.1
9. **Install dev tools** (full only):
   - `bob-nvim` → download binary to `~/.local/bin`, run `bob use stable`
   - `nvm` → curl installer v0.40.1
   - `node` → `nvm install --lts`
   - `tldr` → `pipx install tldr && tldr --update`
10. **Finish** — `exec zsh -l`

### Idempotency

Each step guarded with existence checks (`command -v`, `[ -d ... ]`, `[ -f ... ]`) so re-running is safe.

### WSL awareness

Detect WSL via `/proc/version` for informational logging. The dotfiles themselves already have their own WSL guards (clipboard, `open()`, etc.). The goal is to support both WSL and native Linux.

---

## Makefile

Carries over the existing stow commands:

```makefile
stow:    # stow all packages
unstow:  # unstow all packages
restow:  # unstow then stow (useful after adding new files)
```

---

## Testing

### Principle: the agent writes, the human verifies

The agent MUST NOT execute `setup.sh`, `docker-run.sh`, or any `docker compose` commands. Testing is performed manually by the developer inside a container. The agent may run read-only checks on the host (e.g. `shellcheck setup.sh`) before handing off to the developer.

### Container setup

The `docker-compose.yml` mounts the **repo root** into the container so that edits made by the agent on the host are immediately visible inside — no rebuild required for script changes:

```yaml
volumes:
  - ./:/home/devuser/code/dotfiles
```

The `docker-run.sh` script drops you into a shell rather than auto-running the bootstrap. You run `setup.sh` manually from inside the container:

```bash
# Start the container (or rebuild from scratch)
docker compose up -d --build dotfiles-fedora

# Drop into a shell as devuser
docker compose exec dotfiles-fedora bash

# Inside the container — run manually and observe output
bash ~/code/dotfiles/setup.sh --slim
bash ~/code/dotfiles/setup.sh --full
```

### Clean vs. incremental runs

| Mode | When to use | How |
|---|---|---|
| **Incremental** | Agent patched something, re-test quickly | Re-run `setup.sh` inside existing container (idempotency makes this safe) |
| **Clean slate** | Final verification, or something broke badly | `docker compose down && docker compose up -d --build` |

### Test order

1. `--slim` on Fedora 42 (primary target)
2. `--full` on Fedora 42
3. `--slim` on Ubuntu as a sanity check

### Docker files

- `Dockerfile.fedora` / `Dockerfile.ubuntu` — same pattern (devuser, passwordless sudo), no Ansible pre-install
- **Primary test target: Fedora 42**

---

## What Gets Dropped

| Item | Reason |
|---|---|
| `ansible/` directory | Entire thing removed |
| `bin/bootstrap` | Replaced by `setup.sh` |
| `ansible-lint` dev tool install | No longer relevant without Ansible |
| `.dotfiles/` subdirectory nesting | Dotfiles live at repo root |
| `requirements.yml` (Galaxy) | No more Ansible |

---

## Task Checklist

- [ ] Clone this repo to `~/code/dotfiles` (fresh start, history preserved as reference)
- [ ] Move dotfiles from `.dotfiles/{zshrc,zprofile,tmux,nvim,aider}/` to repo root
- [ ] Write `setup.sh` with slim/full profiles and idempotency guards
- [ ] Write `Makefile` for stow operations
- [ ] Update `Dockerfile.fedora` and `Dockerfile.ubuntu` (remove Ansible)
- [ ] Update `docker-compose.yml` mount paths
- [ ] Update `docker-run.sh` to call `setup.sh`
- [ ] Write `README.md`
- [ ] Verify full install in a clean Fedora 42 container 
