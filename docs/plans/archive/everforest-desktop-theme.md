# Implementation Plan: Everforest desktop theme

Status: complete. The shell UI, terminal/editor, native GTK, and Spek Flatpak
stages are visually accepted. Adwaita icons and the default cursor remain in
place as deliberate finishing choices.

## Goal

Replace the current Gruvbox styling with a cohesive, fixed Everforest theme
across the Hyprland desktop and terminal tools. The result should preserve the
warmth and low-glare readability that works well in the terminal while making
larger desktop surfaces feel calmer and more intentional.

The proposed direction is:

- Everforest Dark, medium contrast
- fixed palette rather than wallpaper-generated colors
- compact layout with small, soft corners
- green used selectively for focus and active states
- opaque surfaces and restrained decoration
- whole-desktop scope, including GTK application chrome

## Why reconsider the current theme

The current Waybar, Wofi, Kitty, tmux, and Neovim configurations share a
Gruvbox palette, but the desktop does not yet have a complete visual system:

- Hyprland has tight gaps and no borders, rounding, shadows, or managed colors.
- Waybar is square and borderless while Wofi is rounded and outlined.
- Mako is launched without a managed configuration.
- GTK applications, dialogs, tray menus, icons, and cursors inherit external
  defaults.
- The local wallpaper has no fallback or documented relationship to the theme.
- Kitty contains overlapping tab color declarations.
- Colors are repeated as literals with no explicit semantic role mapping.

A palette swap alone would retain most of these inconsistencies. The migration
should therefore establish a small desktop design language as well as replace
the colors.

## Proposed palette

Use the official Everforest Dark medium palette, assigning colors by UI role:

| Role | Color | Intended use |
|---|---|---|
| Background | `#2d353b` | Primary windows and bar background |
| Surface | `#343f44` | Modules, inputs, tabs, and notifications |
| Raised surface | `#3d484d` | Hover and selected containers |
| Foreground | `#d3c6aa` | Primary text |
| Muted | `#859289` | Inactive and secondary text |
| Accent | `#a7c080` | Focus, active workspace, and positive state |
| Warning | `#dbbc7f` | Degraded or attention state |
| Urgent | `#e67e80` | Errors, urgent workspaces, and critical alerts |
| Informational | `#7fbbb3` | Links and informational state |

Reference: [Sainnhe's Everforest palette](https://github.com/sainnhe/everforest/blob/master/palette.md).

These are semantic roles, not a rule that every application must display every
color. Green should identify interaction and focus rather than fill large areas
of the desktop.

## Geometry and visual language

Apply the following rules consistently across managed desktop surfaces:

- use approximately 6px corner radii for windows, launchers, modules, tooltips,
  and notifications
- keep spacing compact, with enough separation to distinguish surfaces
- use thin muted borders by default and green borders only for focus
- avoid pill-shaped modules and large accent-colored blocks
- prefer opaque surfaces over blur-heavy or translucent styling
- keep shadows subtle and functional rather than decorative
- continue using JetBrainsMono Nerd Font Mono for shell UI glyph support

Exact values should be adjusted after testing at the workstation's real scale.

## Scope

### Hyprland

Update `hypr/.config/hypr/dotfiles.lua` to define the compositor side of the
visual language:

- add small window rounding
- enable thin active and inactive borders
- use Everforest green for the active border and a muted surface color for the
  inactive border
- increase the current `2`/`4` gaps only enough to make rounded windows legible
- add a restrained shadow if supported cleanly by the Lua configuration API
- retain the existing animation style unless it looks inconsistent after the
  geometry changes
- keep the current no-lock idle policy unchanged

Do not introduce transparency or a blur pipeline as part of the first pass.

### Waybar

Update `waybar/.config/waybar/style.css` without substantially changing the
current module set:

- use the Everforest background, surface, foreground, and muted roles
- give right-side modules small corner radii and consistent spacing
- replace the large yellow active workspace and clock fills with restrained
  green focus treatment
- style hover, urgent workspace, muted audio, and disconnected network states
- keep the full-width top bar rather than converting it into a floating pill
- retain the current compact 30px height unless visual testing shows that a
  small adjustment is needed

### Wofi

Update `wofi/.config/wofi/style.css` so the launcher shares Waybar's hierarchy:

- use the same font family name as Waybar and Kitty
- use a muted outer border with a small radius
- use surface colors for the search input and entries
- show selection with a raised surface plus green text or border rather than a
  bright full-row fill
- preserve the current centered, fixed-size launcher behavior initially

### Mako

Add a new `mako` Stow package containing `.config/mako/config`:

- use opaque Everforest background and foreground colors
- match the 6px radius, thin border, font, and compact spacing
- use the global style for normal urgency and define low and critical overrides
- reserve red for genuinely critical notifications
- keep notification positioning and timeouts conservative

Adding this package requires updating `Makefile`, `README.md`, and `AGENTS.md`
according to the repository's Stow package convention.

### Kitty

Replace `kitty/.config/kitty/current-theme.conf` with a complete Everforest Dark
medium terminal palette and update `kitty.conf`:

- map the ANSI colors to the official Everforest terminal roles
- make selection, cursor, URL, and tab colors intentional
- use green for the active tab without creating a large high-contrast block
- remove duplicate or invalid tab declarations so only one source controls each
  setting
- retain the existing font, font size, hidden decorations, and tab layout unless
  they conflict visually with the new theme

### tmux

Replace the Gruvbox literals in `tmux/.tmux.conf`:

- preserve the current statusline structure and behavior
- use Everforest surfaces for the statusline and inactive windows
- use green selectively for the current window
- map bell and warning states to the urgent and warning roles
- verify Powerline separators against the new adjacent backgrounds

The server-specific tmux configuration should remain independent unless a
separate decision is made to theme remote/headless environments too.

### Neovim

Replace Gruvbox with `neanias/everforest-nvim`:

- use dark mode with medium contrast
- retain the current preference for non-italic strings, comments, operators,
  and folds where supported
- update lualine to use its Everforest integration
- replace the pure-black `nvim-notify` background with the theme background
- update `lazy-lock.json` through the normal Lazy.nvim workflow
- review completion, floating-window, diagnostics, and Git highlight contrast

This native Lua implementation provides Treesitter, LSP, and lualine support
while preserving explicit Dark Medium and non-italic settings.

### GTK applications

Use the maintained
[Everforest GTK theme](https://github.com/Fausto-Korpsvart/Everforest-GTK-Theme)
rather than vendoring generated theme assets into this repository.

The pinned revision is `fede1614cf9a44a03cab25a525f28ff677c1596d` from
upstream PR #35. It is based on `9b8be4d6648ae9eaae3dd550105081f8c9054825`
and removes one GTK4-only property that fails GTK3 parsing. The selected variant
is installed as `Everforest-Green-Dark-Compact-Medium` with:

- dark color variant
- medium Everforest contrast
- compact sizing
- green accent
- libadwaita support where practical

Keep installation in `docs/setup_hyprland.md`, not `setup.sh`, because Hyprland
and its desktop dependencies are deliberately manual and under evaluation.
The opt-in `gtk` Stow package manages GTK3 and GTK4 settings plus safe GTK4 CSS
imports. The upstream installer owns only its generated theme directories and
does not manage files under `~/.config/gtk-4.0`.

GTK work should also consider:

- GTK3 and GTK4 application consistency
- libadwaita limitations and upgrade risk
- Flatpak filesystem access as an optional, explicitly documented step
- lxpolkit dialogs and tray menus
- a compatible dark icon theme
- a neutral cursor theme that does not compete with the green accent

Do not add external theme installation to the general workstation profiles.

### Wallpaper

Keep `~/Pictures/Wallpapers/current.jpg` local and untracked. Do not generate the
palette from the wallpaper.

Add a solid `#2d353b` swaybg fallback when the configured image is absent.
Document a preference for dark, desaturated forest, landscape, or abstract
wallpapers that leave enough visual space behind windows. The repository should
not redistribute a wallpaper unless its license and long-term suitability are
explicitly reviewed.

## Palette ownership

The palette is fixed, so avoid introducing a general-purpose theme engine in the
first implementation. Keep each application's configuration native and map its
colors to the semantic roles in this document.

If literal drift becomes a maintenance problem, a later change can add a small
generator or shared format-specific fragments. Do not add that complexity before
there is a demonstrated need.

## Suggested rollout

Implement and evaluate the migration in reversible stages:

1. Theme Hyprland, Waybar, Wofi, and a new Mako configuration.
2. Test the shell UI for several normal work sessions and adjust contrast,
   spacing, and active-state prominence.
3. Theme Kitty, tmux, and Neovim after the desktop direction feels correct.
4. Install and evaluate the external GTK theme separately.
5. Add managed GTK settings only after confirming GTK3, GTK4, libadwaita, and
   Flatpak behavior on the actual workstation.
6. Review icons, cursor, and wallpaper as finishing elements rather than letting
   them block the core migration.

Keep changes split into coherent commits so an unsuccessful application layer
does not require reverting the terminal or shell work.

## Rollback protocol

Rollback must be prepared before any theme is activated. The Git-managed shell
and terminal configuration is straightforward to restore, but GTK settings,
Flatpak overrides, and externally installed assets require an explicit record.

### Before implementation

1. Create a dedicated feature branch. Do not implement or commit the migration
   directly on `main` or `master`.
2. Confirm that the current Gruvbox configuration is committed and that the
   worktree changes included in the migration are understood.
3. Record the current desktop settings in a local rollback note that is not
   committed if it contains machine-specific information. At minimum, capture:
   - GTK theme
   - icon theme
   - cursor theme and cursor size
   - preferred color scheme
   - any existing Flatpak filesystem overrides related to themes or icons
4. Inventory existing files and symlinks under `~/.themes`, `~/.icons`,
   `~/.config/gtk-3.0`, and `~/.config/gtk-4.0` before installing the external
   theme.
5. Back up any regular GTK configuration file that an upstream installer would
   replace. Prefer identifiable symlinks over copied or overwritten GTK4 assets
   where the upstream theme supports them.
6. Keep or pre-fetch the pinned Gruvbox Neovim plugin revision if offline
   rollback is a requirement. Lazy.nvim otherwise needs network access to
   reinstall it after the Everforest plugin replaces its local checkout.

The implementation must not assume that removing a Stow package also restores
external GTK or Flatpak state.

### Commit boundaries

Keep the rollout stages independently reversible:

1. Hyprland, Waybar, Wofi, and Mako
2. Kitty, tmux, and Neovim
3. GTK settings and documented external-theme integration
4. Optional icons, cursor, Flatpak overrides, and wallpaper refinements

Each stage should be visually evaluated before the next stage begins. Do not
combine external GTK activation with the initial shell styling commit.

### Restoring Gruvbox

If the new Mako or GTK package has been Stow-linked, remove those links from the
revision that still contains the packages before switching branches or
reverting commits. These Stow operations still require explicit user
confirmation. If the branch was already switched, remove only verified symlinks
that resolve into this repository's packages; do not remove regular user
configuration.

If Everforest is rejected before the feature branch is merged, switch back to
the previous branch and reapply the repository's Stow links only with explicit
user confirmation. If the migration has already been merged, use new revert
commits for the relevant stages rather than rewriting history.

After the Git-managed files are restored:

1. Restore the recorded GTK, icon, cursor, cursor-size, and color-scheme values.
2. Remove only GTK4 files or symlinks created by the Everforest installation;
   do not delete pre-existing user files.
3. Remove only the Flatpak overrides added for Everforest.
4. Remove only the three inventoried Everforest theme directories. Do not use
   this pinned installer's removal mode because it unconditionally deletes GTK4
   configuration paths.
5. Reload or restart Hyprland components and graphical applications as needed.
6. Verify Waybar, Wofi, Mako, Kitty, tmux, Neovim, GTK3, GTK4, tray menus, and
   file dialogs against the restored Gruvbox configuration.
7. Inspect the worktree and home-directory theme paths to confirm that no
   unintended Everforest files or broken symlinks remain.
8. After restoring the Neovim lockfile, run Lazy.nvim's restore operation to
   reinstall the pinned Gruvbox plugin. This step requires network access unless
   its checkout or Git objects were retained locally.

Installing an external theme is allowed to leave its inert assets on disk if
switching away from it fully restores the desktop and removal would risk other
files. Correctly restored settings are more important than aggressive cleanup.

## Repository changes

Expected existing files to modify:

- `hypr/.config/hypr/dotfiles.lua`
- `waybar/.config/waybar/style.css`
- `wofi/.config/wofi/style.css`
- `kitty/.config/kitty/kitty.conf`
- `kitty/.config/kitty/current-theme.conf`
- `tmux/.tmux.conf`
- `nvim/.config/nvim/lua/plugins/colorscheme.lua`
- `nvim/.config/nvim/lua/plugins/ui.lua`
- `nvim/.config/nvim/lazy-lock.json`
- `Makefile`
- `README.md`
- `AGENTS.md`
- `docs/setup_hyprland.md`

Expected new files if the relevant stages are accepted:

- `hypr/.config/systemd/user/hyprland-session.target`
- `mako/.config/mako/config`
- GTK3/GTK4 settings under the `gtk` Stow package

Do not change `setup.sh` merely to install or activate the desktop theme.

## Verification

Before any commit:

1. Review all changed colors against the semantic palette table.
2. Check CSS and configuration syntax with the tools available in the repo or
   installed desktop session.
3. Start Waybar, Wofi, Mako, Kitty, tmux, and Neovim independently and inspect
   their logs for invalid settings.
4. Verify normal, hover, selected, muted, disconnected, warning, and urgent
   states where the component supports them.
5. Check both focused and unfocused windows against a representative wallpaper.
6. Verify text and icon legibility at the workstation's real display scale.
7. Verify GTK3, GTK4, libadwaita, lxpolkit, tray menus, and file dialogs before
   declaring the whole-desktop stage complete.
8. Confirm that missing external GTK assets degrade acceptably rather than
   leaving applications unreadable.
9. Run relevant Neovim headless checks and confirm the plugin lockfile contains
   only intended changes.
10. Inspect `git diff` and verify that no local wallpaper, generated GTK assets,
    or machine-specific data has entered the repository.

Live component reloads, Stow operations, external theme installation, and GTK
system-setting changes must only be performed with explicit user confirmation.

## Final decisions

- Everforest Dark medium has acceptable Waybar contrast in normal use.
- Active windows use the proposed 2px green border.
- The existing Powerline tab and tmux statusline shapes remain in place.
- Adwaita icons and the default cursor remain deliberately unchanged.
- Server tmux remains independent from the workstation theme.

## Non-goals

- dynamic wallpaper palette generation
- a general theme switcher or theme framework
- adding Hyprland packages to `setup.sh`
- introducing a lock screen or changing the idle policy
- replacing Waybar, Wofi, Mako, swaybg, Kitty, or tmux
- distributing an external wallpaper or GTK theme in this repository
- changing application behavior solely for visual novelty
