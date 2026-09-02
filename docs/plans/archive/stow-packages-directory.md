# Implementation Plan: Move Stow packages under `packages/`

Status: complete, 2026-09-02. Implemented on `chore/stow-packages-directory`.

## Goal

Reduce root-level clutter by placing every GNU Stow package under one
`packages/` directory while retaining the current one-package-per-application
model and all home-relative package layouts.

The resulting repository shape will be:

```text
dotfiles/
├── packages/
│   ├── bashrc-server/
│   ├── claude/
│   ├── espanso/
│   ├── foot/
│   ├── gtk/
│   ├── hypr/
│   ├── mako/
│   ├── nvim/
│   ├── opencode/
│   ├── themes/
│   ├── tmux/
│   ├── tmux-server/
│   ├── vim-server/
│   ├── waybar/
│   ├── wofi/
│   ├── zprofile/
│   └── zshrc/
├── scripts/
├── docs/
├── Makefile
├── setup.sh
└── container files
```

GNU Stow packages do not need to be at repository root. The Makefile can pass
`--dir=$(CURDIR)/packages`; each package's internal `.config`, `.local`, and
home-file layout remains unchanged.

## Scope

Included:

- move all current Stow packages into `packages/`
- update Makefile Stow invocations to use that directory
- preserve the existing workstation, server, GTK, and Foot package sets
- migrate currently active host links only with explicit confirmation
- update generated-theme output and ignored-runtime paths
- remove the Claude hook configuration's clone-location-specific paths
- update active documentation and package-layout guidance
- verify migration in an isolated target before changing host links

Excluded:

- deeper physical grouping such as `packages/desktop/` or `packages/server/`
- combining packages into large profile packages
- changing setup profiles or installed system packages
- reorganizing `docs/`, redesigning theme generation, or cleaning unrelated
  local residue such as `nohup.out`, `.obsidian/`, and the empty `xkb/`
  directory

Logical grouping should live in Make variables rather than another level of
physical directories. That preserves the ability to Stow applications
independently and avoids multiple Stow roots.

## Current Constraints and Risks

- Existing links resolve into root-level package paths. Moving the directories
  first would leave broken symlinks.
- `tmux` and `tmux-server` both own `~/.tmux.conf`; they are mutually
  exclusive. The migration must preserve whichever profile is currently active.
- `themes` is shared by the default workstation set and `stow-foot`. The
  existing `unstow-foot` asymmetry must be deliberately retained or corrected,
  not changed accidentally during the move.
- The theme generator currently writes to `themes/.local/...`; its output path
  must move to `packages/themes/.local/...` in the same change.
- `.gitignore` contains root-relative `opencode/` and `themes/` paths that must
  move with their packages.
- `claude/.claude/settings.json` currently hardcodes this clone's absolute hook
  paths. Use a home-relative shell expansion such as `$HOME/.claude/hooks/...`,
  subject to validating Claude's hook command execution, so the configuration
  works after cloning elsewhere.
- Stow directory folding and applications writing through Stow links can place
  runtime files inside package sources. Retain the existing ignores, but verify
  that the move does not cause new tracked or unignored runtime artifacts.

## Implementation

### 1. Prepare a reversible migration

1. Create a short-lived feature branch. Do not commit on `main` or `master`.
2. Inspect `git status` and leave unrelated user changes untouched.
3. Record the active Stow package sets before changing the worktree. Determine
   whether workstation, server, GTK, and Foot-specific links are active by
   inspecting their expected links under `$HOME` and their resolved targets.
4. Run an isolated-target dry run using a temporary empty home directory. It
   must use the future `packages/` source directory and must not initialize or
   alter the real theme-state symlink.
5. Obtain explicit confirmation immediately before modifying live links.

### 2. Move the package source directories

Create `packages/` and move these directories without altering their contents:

```text
bashrc-server  claude   espanso  foot  gtk   hypr  mako  nvim  opencode
themes          tmux     tmux-server  vim-server  waybar  wofi  zprofile  zshrc
```

Keep `scripts/` at repository root. It is a repo-only utility, not a Stow
package. Keep bootstrap files, container files, and documentation at root.

### 3. Update Stow orchestration

In `Makefile`:

1. Add a `STOW_DIR` variable based on `$(CURDIR)/packages`.
2. Pass `--dir=$(STOW_DIR)` to every Stow invocation, including delete and
   restow paths.
3. Keep package names unchanged in the existing package-set variables.
4. Split the default package list into clearly named logical groups if that
   improves readability, for example core, desktop, AI, and extras, then derive
   the default workstation list from them. Do not change package membership
   during this layout migration.
5. Decide and document the `stow-foot`/`unstow-foot` ownership behavior. The
   safer default is to retain current behavior: `stow-foot` includes `themes`
   and `foot`; `unstow-foot` removes only `foot` because themes may be shared.

`setup.sh` already invokes Make from the repository root, so it should not need
a behavioral change once the Makefile supplies the Stow source directory.

### 4. Update package-path consumers

Update all active references to package source paths:

- Change `THEMES_DIR` in `scripts/generate-themes.py` to
  `ROOT / "packages" / "themes" / ".local" / "share" / "dotfiles" / "themes"`.
- Move the OpenCode runtime ignore paths to
  `packages/opencode/.config/opencode/...`.
- Move the theme runtime-state ignore path to `packages/themes/.local/state/`.
- Update all active repository-source examples in `README.md` and `AGENTS.md`.
- Update current backlog references only where they identify source paths. Keep
  archived plans historically accurate unless they are used as active guidance.
- Make Claude hook commands portable and verify that `$HOME` expansion works in
  the hook execution context.

Do not edit generated theme fragments by hand. Run the generator after updating
its output location so the checked-in generated files are reproduced at their
new paths.

### 5. Migrate host links

Only after the isolated test passes and the user explicitly approves host
changes:

1. Unstow precisely the package sets recorded in preparation, using the old
   root-level source directory while those directories still exist.
2. Confirm that only repository-managed links were removed and that no regular
   configuration file was deleted.
3. Move the package directories and apply the Makefile/path updates.
4. Stow the same previously active package sets from `packages/`.
5. Initialize theme state only if it was absent before migration. Do not replace
   an existing selected-theme symlink.
6. Resolve representative links from each active set and confirm they point
   into `packages/`.

If host migration cannot be done in the same controlled session, complete and
verify the repository migration separately, then document exact old-layout
unstow and new-layout restow commands for the operator. Never move packages
while active links still point at them.

## Verification

Run these checks before any live migration:

```bash
make themes-generate
make themes-check
bash -n setup.sh
```

Use a disposable target directory to verify every package set without touching
`$HOME`:

```bash
workstation_target="$(mktemp -d)"
server_target="$(mktemp -d)"
gtk_target="$(mktemp -d)"
stow --dir="$PWD/packages" --target="$workstation_target" \
  zshrc zprofile tmux nvim foot themes hypr waybar wofi mako opencode claude espanso
stow --dir="$PWD/packages" --target="$server_target" \
  bashrc-server tmux-server vim-server
stow --dir="$PWD/packages" --target="$gtk_target" gtk
```

`tmux` and `tmux-server` require separate targets because both provide
`.tmux.conf`.

Verify:

- `make themes-check` reports generated output is current
- expected links in isolated targets resolve under `packages/`
- Stow reports no source-directory or target conflicts
- `make stow`, `make stow-server`, `make stow-gtk`, and `make stow-foot` use
  `--dir=$(CURDIR)/packages`
- delete and restow targets still work against isolated targets
- `theme-set` is executable from the isolated workstation target and retains
  its atomic selection behavior
- the Claude hook command resolves after cloning the repository outside its
  current absolute path
- `git diff --check` passes and no generated or runtime artifacts are
  unintentionally added

After explicit approval and live migration, verify the active links in `$HOME`
resolve into `packages/`, then start fresh shell and tmux sessions to confirm
their managed configurations load normally. Desktop applications only need
file-link checks unless a separate live desktop validation is approved.

## Documentation Updates

Update in the implementation commit:

- `README.md` package table and Makefile target table, including missing Claude,
  Espanso, and Foot-only target coverage
- `AGENTS.md` repository tree, Stow-package examples, default package list, and
  generated-theme source/output description
- relevant active setup documentation when it names repository source paths

## Completion Criteria

The migration is complete when the repository root contains no Stow package
directories, all packages reside directly under `packages/`, all package sets
can be Stowed from an isolated target, theme generation remains deterministic,
and any explicitly approved live links resolve to the new source paths without
changing selected runtime theme state or profile behavior.

## Completion Notes

All 17 packages now live under `packages/`, and the Makefile passes that
directory explicitly to every Stow command. The active workstation links were
unstowed before the move and restored from their new paths afterward.

Fresh-target verification found and fixed a Stow directory-folding edge case:
`stow` and `stow-foot` now create `$HOME/.local/state` before linking the
themes package, preventing `theme-set` runtime state from being written into
the package source directory.
