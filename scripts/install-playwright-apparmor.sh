#!/usr/bin/env bash
# Install an AppArmor profile that lets Playwright's managed Chromium create user
# namespaces, so its sandbox works on Ubuntu 24.04+ servers without --no-sandbox.
# Run as the login user that runs the Playwright MCP; it calls sudo itself.
# Safe to re-run. Does nothing on systems without AppArmor user-namespace limits.
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "install-playwright-apparmor: run as the login user, not root (the profile is for \$HOME)" >&2
  exit 1
fi

restrict=$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)
if [ "$restrict" != 1 ]; then
  echo "install-playwright-apparmor: user namespaces are not restricted here, nothing to do"
  exit 0
fi
if ! command -v apparmor_parser >/dev/null 2>&1; then
  echo "install-playwright-apparmor: apparmor_parser not found" >&2
  exit 1
fi

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/apparmor/playwright-chromium.in"
dest=/etc/apparmor.d/playwright-chromium
profile=$(sed "s|@HOME@|$HOME|g" "$src")

if [ -f "$dest" ] && [ "$(cat "$dest")" = "$profile" ]; then
  echo "install-playwright-apparmor: $dest is up to date"
  exit 0
fi

printf '%s\n' "$profile" | sudo tee "$dest" >/dev/null
sudo apparmor_parser -r "$dest"
echo "install-playwright-apparmor: installed $dest"
