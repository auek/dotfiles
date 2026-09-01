# Theme Switching Follow-ups

Status: active. Started 2026-08-31. Milestone 1 is complete and merged via
PR #56. Milestone 2 is complete and merged via PR #57. Live reloading is next
in milestone 3.

## Goal

Extend the completed theme switcher so a selected theme consistently covers the
core Hyprland shell, then remove palette duplication and improve live reloads
only where doing so is safe and useful.

Baseline: `docs/plans/archive/theme-switching-poc.md` and the `theme-set`
command in the `themes` Stow package. The baseline covers Foot, tmux, Neovim,
and Waybar through `~/.local/state/dotfiles/theme/current`.

Everforest's canonical palette is Dark Hard with green accents. The existing
medium/aqua Waybar palette is transitional and will be aligned in milestone 2.

## Scope Boundaries

This work covers the core session shell:

- Foot, tmux, Neovim, and Waybar
- Hyprland colors
- Wofi
- Mako
- swaybg fallback color

This work does not cover:

- GTK, libadwaita, Flatpak, or OpenCode theming
- icon or cursor themes
- theme-specific wallpaper images
- a general desktop-theming framework

Wallpaper assets remain local and untracked. The shared wallpaper path is
`~/Pictures/Wallpapers/current.png`; only the fallback color may follow the
selected theme.

## Milestone 1: Core Hyprland Shell Coverage (Complete)

Add native fragments to every theme pack:

```text
<theme>/
├── foot.ini
├── tmux.conf
├── nvim.lua
├── waybar.css
├── hyprland.lua
├── wofi.css
├── mako.conf
└── swaybg-color
```

Use each component's native configuration mechanism:

- Wofi loads `current/wofi.css` with its `colors=` setting; the base stylesheet
  uses Wofi's color macros directly.
- Mako includes `~/.local/state/dotfiles/theme/current/mako.conf`.
- Hyprland loads pure palette data from `current/hyprland.lua` with `dofile()`.
- Hyprland reads `current/swaybg-color` to construct swaybg's fallback color.

Keep behavior and layout outside theme fragments. In particular, Hyprland
gaps, borders widths, rounding, opacity, animations, and blur stay in
`dotfiles.lua`; Wofi and Mako retain their non-color options in their base
configuration.

Before changing `current`, `theme-set` must verify every required fragment is
present. It must also validate the selected symlink target when queried and
replace the symlink atomically from within the state directory.

Live reload is not part of this milestone. Wofi picks up its stylesheet when
launched; the remaining newly covered components update on their next reload or
new session.

### Acceptance Criteria

- Both Gruvbox and Everforest contain every required fragment.
- Hyprland borders, shadow, and swaybg fallback color follow the selected
  theme.
- Wofi and Mako use the selected palette.
- Existing layout and runtime behavior are unchanged.
- Invalid or incomplete theme packs do not change `current`.
- `hyprctl configerrors` reports no configuration errors in a Hyprland session.
- Runtime state remains outside the worktree.

### Completion Notes

Implemented and merged in PR #56. Static checks and live checks for tmux, Foot,
Neovim, Waybar, Wofi, Mako, and Hyprland configuration passed. The swaybg
fallback is implemented, but its visual live-session check is deferred for a
follow-up report.

## Milestone 2: Semantic Palettes and Generated Fragments (Complete)

Once native fragments establish the real shared color roles, replace repeated
application literals with one semantic palette per theme. Generate native
fragments for all supported applications, while keeping generated output in the
theme packs and the runtime selector dependency-free.

Use a repo-only generator under `scripts/`, with JSON palette sources and
Python's standard library. Do not introduce a runtime template engine or a new
system dependency.

The palette must define the roles needed by the generated fragments:

- backgrounds and surfaces
- borders
- foreground and muted foreground
- accent, warning, and urgent colors
- ANSI terminal colors
- application metadata where needed, such as a Neovim colorscheme name

The generator must be deterministic and provide a check mode that detects
missing semantic roles, unresolved template values, stale generated output, and
incomplete theme packs.

This milestone aligns Waybar's Everforest colors with the canonical Dark
Hard/green palette.

### Acceptance Criteria

- Each color role has one source of truth per theme.
- Generated fragments preserve intended behavior and native syntax.
- Generation is idempotent and checked-in output is current.
- `theme-set` continues to switch only the runtime symlink.

### Completion Notes

Implemented and merged in PR #57. Fragments are generated with
`scripts/generate-themes.py` from one JSON palette per theme
(`scripts/palettes/`) and shared templates (`scripts/templates/`), with
`make themes-generate` and `make themes-check`. Generation is deterministic and
atomic; check mode detects missing roles, unresolved values, stale output,
incomplete packs, and orphan packs. Gruvbox output is byte-identical to the
previous hand-written fragments. Everforest Waybar aligns to canonical Dark
Hard/green, and the stray Everforest borders unify on the Dark Hard border role.
`theme-set` still switches only the runtime symlink.

## Detour: Per-theme Wallpapers (Complete)

Small detour outside the original milestone scope. Each theme pack now carries a
`wallpaper-name` fragment generated from a `meta.wallpaper` role in the palette
(e.g. `everforest`, `gruvbox`). A session-scoped `swaybg.service` user unit
(started by `hyprland-session.target`) runs the `swaybg-current` helper, which
reads the selected theme's name and searches
`~/Pictures/Wallpapers/<name>.png|.jpg|.jpeg`; `swaybg` uses the first match in
fill mode, falling back to the theme's `swaybg-color` when no image is present.
Wallpaper images remain local and untracked (public repo policy). `theme-set`
restarts `swaybg.service` after switching, so the background follows the theme
live without logging out.

## Milestone 3: Live Reloads

Add reload behavior after the integration paths and generated fragments are
stable. A successful theme selection must not be reported as failed solely
because an optional running application cannot reload; each reload action is
independent and warnings are best effort.

| Component | Reload behavior |
| --- | --- |
| tmux | Keep sourcing the selected fragment. |
| Waybar | Keep `SIGUSR2`, with complete command guards. |
| Wofi | No hook; it reads its stylesheet when launched. |
| Mako | Use `makoctl reload` when available. |
| Hyprland | Use `hyprctl reload config-only` after verifying Lua is reevaluated. |
| swaybg | Restart a session-scoped `swaybg.service`. |
| Neovim | Start with an explicit `:ReloadTheme` command. |
| Foot | Evaluate OSC color updates separately. |

Move swaybg from an unmanaged startup command to a user service tied to
`hyprland-session.target`. Use that service for restarts rather than broad
process matching.

> Completed during the wallpaper detour: `swaybg.service` now runs via
> `hyprland-session.target` (Wants) using the `swaybg-current` helper, and
> `theme-set` restarts it after switching. The remaining Milestone 3 reload
> work is tmux, Mako, Hyprland, Neovim, and Foot.

Do not send Unix signals to arbitrary Neovim processes. Consider remote reload
only after `:ReloadTheme` safely reapplies the colorscheme and dependent plugin
configuration in one instance.

Foot has no safe config-file reload. Do not enable OSC updates by default until
there is a reliable way to address Foot-owned terminals without affecting other
applications or interrupting shells.

### Acceptance Criteria

- tmux and Waybar retain their existing repaint behavior.
- Mako and Hyprland reload when their commands and daemons are available.
- swaybg restarts through its session service.
- Neovim can reload its theme explicitly without restarting.
- Missing applications or failed reloads warn without reverting the selected
  theme.

## Verification

Run static checks for each milestone:

- `bash -n` for `theme-set`
- Lua `loadfile()` checks for theme fragments
- isolated tmux server validation
- Foot configuration validation
- generator check mode after milestone 2
- isolated-home tests for valid, unknown, malformed, incomplete, and broken
  selection states

With explicit confirmation before commands that alter the active session, test
both theme directions in Hyprland:

- launch Wofi
- display and reload a Mako notification
- reload Hyprland and inspect `hyprctl configerrors`
- test swaybg fallback with the local wallpaper unavailable
- confirm tmux and Waybar repaint
- confirm Neovim and Foot behavior appropriate to the completed milestone

Update the active README, `AGENTS.md`, and Hyprland setup documentation when
the implementation changes package contents or the documented wallpaper path.
Keep archived plans historical.

## Keep in Mind

Prefer the smallest abstraction that removes the real inconvenience. Do not
expand into external desktop theming, runtime template engines, generic IPC,
watchers, or unsafe process management without a concrete need.

For this project, being able to read the entire implementation in a few minutes
is a feature.
