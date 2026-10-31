# Shared development tools with mise

Status: implemented on `feat/work-setup`; deployment verification on the work
and home machines remains outstanding. Keep all related changes on this branch.

## Goal

Share a declarative development toolset between native Arch and restricted
RHEL 9.8/WSL without requiring system package repositories for standalone CLI
tools. Node stays at 24.19.0; other selected tools track latest stable releases.
Retain `.nvmrc` and `.node-version` support and ordinary upstream interfaces.

## Scope

Included:

- install mise in the `--full` profile using its recommended Linux installer
- maintain the `mise` Stow package with `~/.config/mise/config.toml`
- pin Node 24.19.0 and enable Node idiomatic version files
- declare latest stable Aqua releases of Bat, Tealdeer, Lazygit, fastfetch,
  ripgrep, fd, fzf, and Neovim
- activate mise for interactive Zsh and expose shims to login/non-interactive
  consumers
- remove overlapping distro installers, Bob installation/PATH overrides, and
  the Python tldr installer; retain the optional Bob configuration package
- add portable Tealdeer configuration using the system certificate trust store
- update the affected repository documentation

Excluded:

- moving Stow, tmux, htop, shell frameworks, uv, llm, or pipx into mise
- deleting existing nvm/Bob/manual installations or migrating npm globals
- changing proxy settings, certificates, credentials, or private configuration
- adding RHEL support to the full bootstrap
- claiming native Windows Git Bash support before the existing VM experiment
  validates mise there

## Approach

1. Use the workstation inventory as the baseline and preserve existing versions
   for Node. Use `latest` for the selected stable CLI releases.
2. Install from declarative configuration without `mise use --global` or other
   commands that rewrite tracked settings. Upgrade explicitly with
   `mise upgrade --no-prune`; do not use `--bump` for routine updates.
3. Use interactive activation and login shims, deduplicate PATH, and prefer
   mise's Neovim over the retained Bob launcher.
4. On restricted RHEL/WSL, pull and directly Stow only the selected packages,
   then run `mise install`; do not run `setup.sh`.
5. Verify both machines before manually removing redundant installations.

## Verification

- Disposable-home checks cover first-command Node/npm/npx and Neovim selection,
  both project version files, inherited subprocess PATH, the retained Bob
  launcher, unique PATH entries, repeatable bootstrap behavior, and Stow
  conflict/removal safety. See `scripts/test-mise.py` (Python 3.11+).
- Test actual downloads and executable startup with published checksums. If
  cloud discovery APIs are unavailable, temporary fixture lockfiles may supply
  verified release URLs; do not commit them or describe ordinary discovery as
  verified from that test.
- Check the current Neovim binary's glibc requirements; a successful cloud
  startup alone does not prove RHEL compatibility for future releases.
- Run shell syntax, existing Hyprland/theme checks, and Neovim smoke tests.
- Work/home deployment, real corporate networking, shell timing, and full
  Fedora/Ubuntu/Arch container provisioning require separate verification.

## Completion Criteria

Repository implementation is ready when the declared tools install and run,
shell selection and Stow checks pass, and bootstrap/documentation agree.
Deployment is complete only after real home/work verification, including
Neovim language servers and proxy-dependent downloads. The previous 1.5-second
work-machine measurement covered the whole shell, not nvm alone; cloud timings
must not be presented as a measured workstation improvement.
