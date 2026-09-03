# Implementation Plan: Arch Linux container support

Status: in progress. Arch detection, the container service, and the repeatable
test runner are implemented. Arch `server`, `slim`, and `full` profiles have
been verified in the container; Fedora and Ubuntu regression tests remain.

## Goal

Add Arch Linux as a supported `setup.sh` target and use a disposable Arch
container to establish that the repository's CLI bootstrap, shell setup, and
Stow packages work before migrating the physical workstation from Fedora.

The container test should answer:

- Does `setup.sh` detect Arch and install the correct Pacman packages?
- Do the `server`, `slim`, and `full` profiles complete in a clean Arch home?
- Can each profile be run a second time without conflicts or duplicate setup?
- Do the expected shell, tmux, Vim, Neovim, and Stow-managed files work?
- Which remaining checks must be performed on the physical Arch installation?

## Current state

The repository has Fedora, Ubuntu, and Arch test images, Compose services, and
`docker/run.sh` support. `setup.sh` detects Arch and installs profile packages
with Pacman. `docker/test.sh` recreates a selected service, runs its profile
twice, and checks commands, login shell, and Stow links.

The `Makefile` and Stow package layout are distro-neutral. Most configuration
files can therefore be exercised on Arch once the required packages exist.

## Scope

### Included

- native Arch detection in `setup.sh`
- Pacman package mappings for all three profiles
- correct Arch full-upgrade behavior without partial upgrades
- an Arch test image and Compose service
- Arch support in `docker/run.sh`
- clean-install and idempotency tests for `server`, `slim`, and `full`
- explicit assertions for installed commands, login shell, and Stow links
- documentation updates for Arch support and container commands

### Not proven by a container

- Hyprland startup or Lua API compatibility
- NVIDIA drivers, kernel modules, DRM/KMS, or hardware acceleration
- Wayland rendering, monitor layout, refresh rate, or screenshots
- PipeWire, WirePlumber, microphones, or speakers
- desktop portals and graphical-session systemd targets
- suspend/resume, Hypridle, logind, or power management
- rootless Podman networking, sockets, cgroups, or nested containers
- GNOME settings through a real graphical session D-Bus

These remain physical-host checks during the desktop-and-workstation stage of
the Arch migration.

## Arch package mapping

Add an `arch` branch to the `/etc/os-release` case in `setup.sh`.

```bash
arch)
  PKG_MANAGER="pacman"
  PKG_INSTALL="sudo pacman -S --needed --noconfirm"
  PKG_SERVER="curl git make stow tmux vim"
  PKG_COMMON="curl github-cli git gcc libatomic make openssh python-pipx python-pip stow tmux unzip zsh"
  PKG_OPTIONAL="eza fd fzf htop bat neovim ripgrep sqlite fastfetch"
  info "Detected: Arch Linux"
  ;;
```

The Arch package names above were verified against the official repositories on
2026-08-24. In particular:

| Command or role | Arch package |
|---|---|
| GitHub CLI (`gh`) | `github-cli` |
| pipx | `python-pipx` |
| pip | `python-pip` |
| `fd` | `fd` |
| SSH client and `ssh-agent` plugin | `openssh` |
| SQLite CLI | `sqlite` |

### Pacman update policy

Arch does not support partial upgrades. Never add a `pacman -Sy` path.

- With `--update`, run `sudo pacman -Syu --noconfirm` before installing the
  selected profile packages.
- Without `--update`, install with `pacman -S --needed --noconfirm` using the
  existing local sync databases; do not refresh them independently.
- Build the Arch container from a fully upgraded base so its package databases
  and installed packages begin in a consistent state.

## Implementation

### 1. Extend `setup.sh`

Add the Arch package mapping and a `pacman` branch to the package installation
step. Preserve the current profile behavior:

- `server` installs only `PKG_SERVER` and keeps Bash as the login shell.
- `slim` installs `PKG_COMMON`, changes the login shell to Zsh, and installs the
  normal workstation Stow packages.
- `full` adds optional CLI packages and the existing external dev tool
  installers.

Keep the current Fedora-only container-tooling step unchanged during the first
pass. Installing Podman on the Arch host is a separate policy decision, and a
Docker container cannot meaningfully validate rootless Podman integration.

Update the unsupported-distro error so it lists Arch, Fedora, and
Ubuntu/Debian.

### 2. Add `docker/Dockerfile.arch`

Base the image on `archlinux:base` and follow the existing Fedora image's user
model:

1. Run a full `pacman -Syu` and install `sudo`.
2. Create `devuser` with a home directory.
3. Add `devuser` to `wheel` and configure passwordless sudo.
4. Remove skeleton `.bashrc`, `.profile`, `.bash_logout`, and `.zshrc` files so
   Stow encounters a clean home.
5. Switch to `devuser`, set `/home/devuser` as the working directory, and keep
   the container alive using the existing entrypoint convention.

Do not install the dotfiles package set in the Dockerfile. `setup.sh` itself
must perform that work so the test exercises the real bootstrap path.

### 3. Extend Compose and the runner

Add `dotfiles-arch` to `docker/compose.yml` with the same repository bind mount
and interactive settings as the Fedora and Ubuntu services.

Extend `docker/run.sh` so:

- help and examples list `arch`
- validation accepts `arch`
- `dotfiles-arch` is selected for `-d arch`
- all three profiles continue to use the same invocation path

Example target commands:

```bash
bash docker/run.sh -d arch -t server
bash docker/run.sh -d arch -t slim
bash docker/run.sh -d arch -t full
```

### 4. Add repeatable assertions

The current runner drops into an interactive shell and reuses a named container.
That is useful for inspection but can hide failures behind state from an earlier
run. Add a small noninteractive test path or script that can:

- remove and recreate only the selected test container
- run a profile to completion
- assert expected commands and links
- run the same profile again to test idempotency
- return a non-zero status when an assertion fails

Keep manual interactive access in `docker/run.sh`; do not replace it with the
test-only path.

## Test protocol

### Static checks

Run before container tests:

```bash
bash -n setup.sh
bash -n docker/run.sh
```

Run ShellCheck as well if it is already available on the host. Do not make a new
host dependency mandatory solely for this change.

### Server profile

Start with `server` because it has the smallest package and configuration
surface.

Verify:

- `curl`, `git`, `make`, `stow`, `tmux`, and `vim` exist
- Bash remains the login shell
- `~/.bashrc`, `~/.vimrc`, and `~/.tmux.conf` point to server packages
- Zsh, Oh My Zsh, and workstation packages are not required
- Bash starts without configuration errors
- tmux parses the server configuration
- a second `setup.sh --server` run succeeds

### Slim profile

Verify:

- all `PKG_COMMON` commands exist under their expected command names
- Zsh is listed in `/etc/shells` and is the user's login shell
- Oh My Zsh and the pinned zsh-autosuggestions checkout exist
- `make stow` creates the expected workstation links
- `zsh -lic exit` completes without startup errors
- tmux parses the workstation configuration
- the GNOME setup script takes its supported headless skip path
- a second `setup.sh --slim` run succeeds without replacing valid links

The container can prove that Hyprland, Waybar, Wofi, Mako, and related files are
stowed. It cannot prove that those applications can run.

### Full profile

Run `full` only after `server` and `slim` pass. It is slower and depends on
several upstream installers.

Verify:

- optional package commands such as `eza`, `fd`, `fzf`, `htop`, `bat`, `rg`,
  `ssh`, `sqlite3`, and `fastfetch` exist
- the native Neovim package starts headlessly with the managed configuration
- NVM and Node LTS install
- `uv`, `tldr`, and `llm` are discoverable in the effective login-shell `PATH`
- Neovim starts headlessly with the managed configuration
- a second `setup.sh --full` run succeeds

Optional-package failures currently produce warnings instead of failing the
setup. The test must assert the expected commands explicitly rather than treating
exit status zero as sufficient.

### Update behavior

Test both Arch paths separately:

- a clean, current image without `--update`
- a clean image with `--update`, confirming that the command performs `-Syu`

The test should fail if `pacman -Sy` appears anywhere in the implementation.

## Host validation after installation

Once container tests pass and Arch boots on the workstation, validate the parts
that need real hardware:

1. Run `setup.sh --slim` first and confirm shell, terminal, tmux, and Stow links.
2. Install the Arch Hyprland and NVIDIA package set manually.
3. Start Hyprland from the chosen login path and check both monitors at 180 Hz.
4. Verify the graphical-session target, portals, notifications, launcher,
   Waybar, screenshots, clipboard, and authentication agent.
5. Verify PipeWire audio and microphone input.
6. Test suspend/resume and TTY recovery.
7. Run `setup.sh --full` only after the base desktop is stable.

Fedora remains available throughout as the known-good fallback.

## Known risks and follow-ups

- Arch's rolling image can change without a repository commit, so a broken build
  may reflect upstream package churn rather than a dotfiles regression.
- The named Compose containers retain state unless explicitly recreated.
- The live repository bind mount can expose ignored local files to Stow tests.
- The `full` profile downloads from several upstream projects and can fail for
  network or rate-limit reasons unrelated to Arch.
- pipx applications under `~/.local/bin` need an effective `PATH` during repeat
  runs; the test should expose any current idempotency problem there.
- Container success must not be presented as proof that the graphical Arch
  workstation is complete.
- Arch-specific Hyprland package instructions belong in
  `docs/setup_hyprland.md`, not in the general container test.

## Files expected to change

- `setup.sh`
- `docker/Dockerfile.arch` (new)
- `docker/compose.yml`
- `docker/run.sh`
- `README.md`
- `AGENTS.md`
- `docker/test.sh`

## Exit criteria

- Arch is detected without affecting Fedora or Ubuntu behavior.
- No `pacman -Sy` partial-upgrade path exists.
- Fresh Arch `server`, `slim`, and `full` profile tests pass.
- Running each profile twice succeeds.
- Tests verify expected commands and links rather than only setup exit status.
- Fedora and Ubuntu container smoke tests still pass.
- Documentation clearly separates container-tested behavior from host-only
  Hyprland, NVIDIA, systemd, and hardware validation.
