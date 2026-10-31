# Shared development tools with mise

Status: shared implementation merged in PR #73. Targeted deployment on a limited
RHEL/WSL machine and migration of the existing Arch workstation are verified.
Full distro bootstrap provisioning remains unverified.

## Goal

Share a declarative development toolset between native Arch and restricted
RHEL 9.8/WSL without requiring system package repositories for standalone CLI
tools. The shared Node default stays at 24.19.0; other selected tools track
latest stable releases. A machine-local `~/.config/mise/config.local.toml` may
override Node without changing the shared pin; the Arch workstation uses `lts`.
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

1. Use the tool inventory as the baseline and preserve existing versions
   for Node. Use `latest` for the selected stable CLI releases.
2. Install from declarative configuration without `mise use --global` or other
   commands that rewrite tracked settings. Upgrade explicitly with
   `mise upgrade --no-prune`; do not use `--bump` for routine updates.
3. Use interactive activation and login shims, deduplicate PATH, and prefer
   mise's Neovim over the retained Bob launcher.
4. On restricted RHEL/WSL, pull and directly Stow only the selected packages,
   then run `mise install`; do not run `setup.sh`.
5. Verify each deployment target before manually removing redundant installations.

## Verification

- Disposable-home checks cover first-command Node/npm/npx and Neovim selection,
  machine-local overrides and their preservation across Stow operations, both
  project version files, inherited subprocess PATH, the retained Bob launcher,
  unique PATH entries, repeatable bootstrap behavior, and Stow conflict/removal
  safety. See `scripts/test-mise.py` (Python 3.11+).
- Test actual downloads and executable startup with published checksums. If
  cloud discovery APIs are unavailable, temporary fixture lockfiles may supply
  verified release URLs; do not commit them or describe ordinary discovery as
  verified from that test.
- Check the current Neovim binary's glibc requirements; a successful cloud
  startup alone does not prove RHEL compatibility for future releases.
- Run shell syntax, existing Hyprland/theme checks, and Neovim smoke tests.
- Targeted RHEL/WSL deployment, proxy-dependent downloads, and selection of the
  migrated binaries have been verified. Full Fedora/Ubuntu/Arch provisioning
  remains unverified.

### Arch workstation migration (2026-10-31)

- Installed mise with its upstream user-local installer, linked only `mise`,
  `tealdeer`, `zshrc`, and `zprofile`, and ran ordinary tool discovery/downloads
  with `mise install`. Repeat installation installed nothing; `mise outdated`
  reported no updates and `mise doctor` reported no problems.
- The local Node `lts` override resolved to 26.13.0 with npm/npx 11.20.0.
  The shared configuration remains pinned to 24.19.0. Fresh login, interactive,
  and interactive-login shells selected mise tools without duplicate PATH
  entries. Both project version files selected 24.19.0, including subprocesses,
  and returned to the LTS default after leaving the project.
- Restored the previously installed Corepack 0.35.0 into the active mise Node
  and re-enabled its pnpm launchers. pnpm 12.4.2 ran successfully. Verify from
  shells without inherited nvm PATH entries: an old installation can otherwise
  mask missing global npm commands.
- Tealdeer 1.9.1 downloaded its cache through the system trust store and displayed
  the Node page. The eight mise checks, seven Hyprland checks, theme consistency,
  and shell syntax checks passed.
- Preserved the default `nvim` Stow profile, its lockfile, and its plugin/Mason
  data. Actual Neovim 0.12.6 startup found all 38 cached plugins (35 loaded at
  startup). Selected theme/reload, statusline, completion loading, Telescope
  file/text search with native fzf, the file tree, and editor split navigation
  passed. Real TypeScript and Python diagnostics, TypeScript definition lookup,
  and Lua, Bash, YAML, and Markdown server attachment passed under the new Node.
  A real TUI in a separate tmux server verified Ctrl-H/L between editor splits
  and terminal panes without saving a modified buffer.
  This does not establish every plugin feature or ESLint/Ansible/Astro behavior.
- Shell startup used the same workstation and environment, one warm-up and
  seven measured runs per mode, with inherited manager PATH entries excluded:

  | Zsh mode | Before | After |
  |---|---:|---:|
  | Login, non-interactive (`-lc`) | 5.0 ms | 8.6 ms |
  | Interactive (`-ic`) | 199.8 ms | 56.9 ms |
  | Interactive login (`-lic`) | 194.4 ms | 65.7 ms |

  These are complete-shell medians, not isolated tool-manager benchmarks.
  Non-TTY FZF `zle` warnings were reproduced with the pre-migration shell
  configuration; they are not a new mise regression.
- Shell configuration copies and the editor lockfile were saved outside the
  worktree under `~/.local/state/dotfiles/mise-migration/`. The previous pipx
  tldr environment and link destinations were also archived there.
- After verification and explicit approval, removed the duplicate Pacman
  packages `bat`, `lazygit`, `fastfetch`, `ripgrep`, `fd`, `fzf`, and `neovim`
  through Pacman, and Python tldr through pipx. None had required reverse
  dependencies; Neovim was optional for pacman-contrib. Package archives remain
  in the Pacman cache, and the nvm-managed Node 24.20.0 installation is retained.
  Fresh-shell tool selection and editor checks were repeated without the
  fallback installations.

## Completion Criteria

Repository implementation is ready when the declared tools install and run,
shell selection and Stow checks pass, and bootstrap/documentation agree.
Deployment is complete only after verification on each target, including
Neovim language servers and proxy-dependent downloads. Measure complete shell
startup on each target; cloud timings must not be presented as a measured
target-machine improvement or attributed solely to one tool manager.
