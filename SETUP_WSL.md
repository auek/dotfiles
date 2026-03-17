# WSL2 Setup Notes

Quirks and fixes for running this dotfiles setup on Fedora 42 under WSL2.

---

## Podman on Fedora 42 + WSL2

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

WSL2's kernel does not support nftables. Podman 5.x on Fedora 42 uses the
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

This is already handled in `.zprofile` (applied after `make stow`):

```zsh
[ -S "/run/user/${UID}/podman/podman.sock" ] && \
    export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
```

Until the dotfiles are stowed, export it manually in your shell:

```bash
export DOCKER_HOST=unix:///run/user/${UID}/podman/podman.sock
```

### Verify everything works

```bash
curl --unix-socket /run/user/${UID}/podman/podman.sock http://localhost/version
bash docker-run.sh -d fedora
```

The curl should return a JSON version response. The docker-run.sh should drop
you into a container shell as `devuser`.

---

## Notes

- The `"/" is not a shared mount` warning is cosmetic on WSL2 and can be ignored.
- The `Emulate Docker CLI using podman` and `Executing external compose provider`
  messages are informational. Create `/etc/containers/nodocker` to suppress the
  first one if desired.
- If the podman socket stops responding after a system restart, run:
  `systemctl --user reset-failed podman.socket podman.service && systemctl --user start podman.socket`
