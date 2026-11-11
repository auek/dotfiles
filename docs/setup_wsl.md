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

## tmux recovery

Workstation slim/full setup installs upstream
[tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) and
[tmux-continuum](https://github.com/tmux-plugins/tmux-continuum) under your home.
This is shared workstation behavior on native Linux and WSL, not a WSL-only
workaround. The minimal server profile is unchanged.

The shared config enables five-minute autosaves and manual restore, with no pane
content capture or automatic tmux startup. Plugins load after the theme and
`~/.tmux.conf.local`; theme changes reinstate the autosave hook. Keep local
settings idempotent because they can run repeatedly. Missing plugins do not
prevent ordinary tmux use, and config loading never downloads software.

### Existing installations and limited machines

From the repository root, install missing plugins without running the full
bootstrap, then link the shared recovery fragment:

```bash
bash scripts/install-tmux-plugins.sh
make restow
```

The installer needs Git and Bash, with no TPM, EPEL, or sudo. Use the existing
HTTPS proxy environment if required; keep certificate verification enabled.
Reviewed revisions live in `scripts/install-tmux-plugins.sh`. New installations
use those pins. Existing plugin paths are preserved without fetching, checking
out, or overwriting local changes; updating them remains an explicit action
after inspecting the checkout and the proposed revision.

If you followed the former manual instructions, keep both plugin directories
and `~/.local/state/tmux/resurrect` unchanged. After restowing, remove the old
standard recovery block from `~/.tmux.conf.local`: its seven `@resurrect-*` /
`@continuum-*` settings and two plugin `run-shell` lines are now shared. Preserve
unrelated settings and any intentional overrides. The old block also works
during the transition, including a pull before restow; cleanup is not automatic.

Reload from inside the running tmux server; do not restart it or close sessions:

```bash
tmux source-file "$HOME/.tmux.conf"
```

### Saving, restoring, and local overrides

Saving is automatic; there is no shared manual-save shortcut. After five minutes,
confirm `~/.local/state/tmux/resurrect/last` points to a snapshot. Continuum checks
from the status line; keep it enabled and a client attached for periodic saving.
Remove any old local `@resurrect-save F5` setting to retire that shortcut too.
After a crash or reboot, start tmux and press **Ctrl+s, then F6** to restore
before the first autosave.
Restoration is manual; neither tmux nor sessions start automatically on login.
Ctrl+s, then Ctrl+s retains its existing send-prefix behavior.

Snapshots restore sessions, windows, pane layouts and directories, plus commands
from Resurrect's default allowlist. They do not preserve process memory,
in-progress builds or unsaved editor buffers. Pane contents are not captured.
State remains in the private directory above, outside the repository.

Override shared defaults in the ordinary, untracked `~/.tmux.conf.local`; do not
Stow it. For example, `set -g @continuum-save-interval '0'` disables autosaving.
To stop autosaving immediately without closing sessions, also run
`tmux set -g @continuum-save-interval 0` in the running server.
