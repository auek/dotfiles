# Implementation Plan: Migrate Node from nvm to mise

Status: later. This records the agreed migration scope; no implementation is
currently scheduled.

## Goal

Replace nvm with mise for global and project-specific Node.js version
management. Reduce shell startup overhead while retaining Node LTS defaults and
support for existing `.nvmrc` and `.node-version` files.

## Scope

Included:

- install mise in the `--full` profile using its recommended Linux installer
- add a `mise` Stow package with `~/.config/mise/config.toml`
- declare Node LTS and enable Node idiomatic version files
- activate mise for interactive Zsh and expose shims to login/non-interactive
  consumers
- remove nvm installation and shell initialization from managed files
- update the affected repository documentation

Excluded:

- moving Bob, Neovim, uv, tldr, llm, pipx, or distro packages into mise
- deleting `~/.nvm` or migrating global npm packages automatically
- claiming native Windows Git Bash support before the existing VM experiment
  validates mise there

## Approach

1. Complete the current Neovim/nvm work separately, then use a new feature
   branch for this migration.
2. Add a Stow-managed global mise config with `node = "lts"` and enable Node's
   `.nvmrc`/`.node-version` compatibility.
3. Update `setup.sh` to install mise idempotently and run `mise install` against
   the declarative config. Do not use `mise use --global`, because it would
   rewrite the Stow-managed file.
4. Replace nvm loading in `.zshrc` with mise PATH activation and add shim
   activation in `.zprofile` for consumers that do not run an interactive
   prompt.
5. Leave the existing nvm installation on disk as a rollback path; document its
   optional manual removal after the migration is proven.
6. Update `README.md`, `AGENTS.md`, and the Windows Git Bash experiment where
   they describe nvm-specific behavior.

## Verification

- run `bash -n setup.sh` and `zsh -n` for the changed shell files
- verify `mise doctor` and `mise ls --current`
- test `node`, `npm`, and `npx` as the first command in fresh login shells
- confirm `node -p process.execPath` resolves to a mise-managed installation
- verify project version switching with an `.nvmrc`
- repeat the Neovim checks for Node-backed LSP servers
- compare fresh-shell startup time with the measured eager-nvm baseline
- test the full profile in Fedora and Ubuntu containers after explicit approval

## Completion Criteria

The migration is complete when mise installs the configured Node LTS version
idempotently, fresh shells and Neovim use that version without nvm, project
version files switch correctly, and the supported Linux/WSL setup documentation
matches the new behavior.
