#!/usr/bin/env bash
# Same container invocation for a local run and GitHub Actions.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
distro="${1:-arch}"
suite="${2:-runtime}"
case "$distro" in arch|rhel9) ;; *) echo "Usage: $0 [arch|rhel9] [runtime|shell|editor|toolchain]" >&2; exit 2 ;; esac
case "$suite" in runtime|shell|editor|toolchain) ;; *) echo "Unknown suite: $suite" >&2; exit 2 ;; esac
image="dotfiles-runtime:$distro"
docker build --build-arg "DISTRO=$distro" -f "$root/docker/Dockerfile.runtime" -t "$image" "$root"
# Fixture preparation happens at build time. Checks run as an unprivileged user
# without network access and with the checkout mounted read-only.
docker run --rm --network none --mount "type=bind,source=$root,target=/repo,readonly" \
    "$image" python3 scripts/check.py "$suite" --fixtures /opt/fixtures
