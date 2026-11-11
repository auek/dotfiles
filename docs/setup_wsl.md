# WSL2 Setup Notes

Quirks and fixes for running this dotfiles setup under WSL2.

The Fedora sections cover WSL-specific exceptions. The optional tmux recovery
setup also works on native Linux and is enabled separately on each machine.

On native Fedora Linux, `setup.sh --full` installs Podman plus Docker-compatible
CLI support automatically. On WSL2, `setup.sh` intentionally skips container
tooling so the WSL-specific path stays explicit and opt-in.

---

## Podman on Fedora 42+ + WSL2

### Install required packages
```bash
sudo dnf install podman podman-docker docker-compose iptables
```

### Fix rootless user namespace mapping

WSL2 strips the setuid bit from `newuidmap`/`newgidmap`, which rootless podman
needs to map UIDs into the user namespace. Restore it:
```bash
sudo chmod u+s /usr/sbin/newuidmap /usr/sbin/newgidmap
```

### Fix container networking (nftables → iptables)

WSL2's kernel does not support nftables. Podman 5.x on Fedora 42+ uses the
`netavark` network backend (CNI is not compiled in) which defaults to nftables.
Force it to use iptables instead:
```bash
sudo tee /etc/containers/containers.conf > /dev/null << 'EOF'
[network]
firewall_driver = "iptables"
EOF
```

### Enable and start the podman socket

The `docker-compose` plugin communicates with podman via a socket. Enable it so
it starts automatically with your user session:
```bash
systemctl --user enable podman.socket
systemctl --user start podman.socket
```

### Set DOCKER_HOST

The `docker-compose` plugin does not pick up the podman socket path
automatically on WSL2. Set `DOCKER_HOST` so all `docker`/`docker compose`
commands work without prefixing it manually.

This is already handled in `.zprofile` when WSL is detected (applied after
`make stow`):
```zsh
if grep -qi microsoft /proc/version 2>/dev/null; then
  [ -S "/run/user/${UID}/podman/podman.sock" ] && \
      export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
fi
```

Until the dotfiles are stowed, export it manually in your shell:
```bash
export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
```

### Verify everything works
```bash
curl --unix-socket /run/user/${UID}/podman/podman.sock http://localhost/version
bash docker/run.sh -d fedora
```

The curl should return a JSON version response. The docker runner should drop
you into a container shell as `devuser`.

---

## WSL Interop Broken on Fedora (systemd + binfmt)

### Symptoms

Windows executables fail with `exec format error`:
```bash
clip.exe
explorer.exe .
cmd.exe /c clip
```

Even though the binaries exist under `/mnt/c/...`.

### Root cause

Fedora uses `systemd`, which manages `binfmt_misc` via `systemd-binfmt`. WSL
also relies on `binfmt_misc` to register its `WSLInterop` handler (interpreter
`/init`). On startup, `systemd-binfmt` overrides and removes the WSL handler,
breaking `.exe` execution.

### Fix

Mask `systemd-binfmt` so WSL retains control of `binfmt_misc`:
```bash
sudo systemctl mask systemd-binfmt
wsl --shutdown  # run from PowerShell
```

### Verify
```bash
ls /proc/sys/fs/binfmt_misc        # should include WSLInterop
cat /proc/sys/fs/binfmt_misc/WSLInterop
```

Expected output:
```
enabled
interpreter /init
```

### Notes

- One-time fix, persistent across restarts.
- If interop breaks again, `wsl --shutdown` from PowerShell usually restores it.
- Trade-off: disables all `systemd-managed` binfmt handlers (e.g. QEMU
  user-mode emulation). Acceptable for a standard dev workstation with no
  cross-arch emulation needs.

---

## Notes

- The `"/" is not a shared mount` warning is cosmetic on WSL2 and can be ignored.
- The `Emulate Docker CLI using podman` and `Executing external compose provider`
  messages are informational. Create `/etc/containers/nodocker` to suppress the
  first one if desired.
- If the podman socket stops responding after a system restart, run:
  `systemctl --user reset-failed podman.socket podman.service && systemctl --user start podman.socket`

## Optional tmux recovery on a limited RHEL/WSL machine

The workstation tmux config sources an ordinary, untracked
`~/.tmux.conf.local` after its theme. `theme-set` reapplies it after theme
changes, so plugins that append status-line jobs keep working. Keep this file
idempotent: it can run repeatedly. Machines without the file keep the shared
defaults; there is no OS detection or automatic plugin installation.

For periodic session snapshots, install upstream
[tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) and
[tmux-continuum](https://github.com/tmux-plugins/tmux-continuum) under your home.
This needs Git and Bash, with no TPM, EPEL, or sudo. Use the existing HTTPS proxy
environment if required; keep certificate verification enabled. These commands
select the reviewed plugin commits. If either directory already exists, inspect
it before changing its checkout.

```bash
mkdir -p "$HOME/.local/share/tmux/plugins"
git clone https://github.com/tmux-plugins/tmux-resurrect.git \
  "$HOME/.local/share/tmux/plugins/tmux-resurrect"
git -C "$HOME/.local/share/tmux/plugins/tmux-resurrect" checkout --detach \
  cff343cf9e81983d3da0c8562b01616f12e8d548
git clone https://github.com/tmux-plugins/tmux-continuum.git \
  "$HOME/.local/share/tmux/plugins/tmux-continuum"
git -C "$HOME/.local/share/tmux/plugins/tmux-continuum" checkout --detach \
  0698e8f4b17d6454c71bf5212895ec055c578da0
install -d -m 0700 "$HOME/.local/state/tmux/resurrect"
```

Create or edit `~/.tmux.conf.local` outside the repository. Preserve any existing
settings, put these plugin loads last, and do not Stow this file:

```tmux
set -g @resurrect-dir "$HOME/.local/state/tmux/resurrect"
set -g @resurrect-save 'F5'
set -g @resurrect-restore 'F6'
set -g @resurrect-capture-pane-contents 'off'
set -g @continuum-save-interval '5'
set -g @continuum-restore 'off'
set -g @continuum-boot 'off'
run-shell '"$HOME/.local/share/tmux/plugins/tmux-resurrect/resurrect.tmux"'
run-shell '"$HOME/.local/share/tmux/plugins/tmux-continuum/continuum.tmux"'
```

After pulling the shared hook, reload from inside the running tmux server:

```bash
tmux source-file "$HOME/.tmux.conf"
```

Press **Ctrl+s, then F5** for an initial save. Confirm
`~/.local/state/tmux/resurrect/last` points to a snapshot. Continuum checks from
the status line and saves when five minutes have elapsed; keep the status line
enabled and a client attached for periodic saving. After a crash or reboot,
start tmux and press **Ctrl+s, then F6** to restore before the first autosave.
Restoration is manual; neither tmux nor sessions start automatically on login.
Ctrl+s, then Ctrl+s retains its existing send-prefix behavior.

Snapshots restore sessions, windows, pane layouts and directories, plus commands
from Resurrect's default allowlist. They do not preserve process memory,
in-progress builds or unsaved editor buffers. Pane contents are not captured.
State remains in the private directory above, outside the repository.

To enable the same setup later on another machine, repeat these local steps.
Removing the local file stops loading plugins on the next tmux server start;
an existing server keeps its loaded bindings/options until restarted. To stop
autosaving immediately without closing sessions, run
`tmux set -g @continuum-save-interval 0`.
