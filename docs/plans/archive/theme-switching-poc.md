# Theme Switching POC

Status: complete. The shared theme-pack switcher is implemented for Foot,
tmux, Neovim, and Waybar, and all first-version checks pass. Follow-up ideas
(live reload for Foot and Neovim, a semantic palette) live in
`docs/plans/theme-switching-follow-ups.md`.

## Goal

Build a very small personal theme switcher for a Linux setup, inspired by Omarchy's theming architecture without trying to reproduce Omarchy.

The purpose is to make switching themes across a few tools easier while keeping the implementation small enough to fully understand and maintain.

Initial scope:

- Foot
- tmux
- Neovim
- Waybar

The POC should answer one main question:

> Can a few independently configured applications share a simple "current theme" abstraction so that changing theme becomes one command instead of manually editing several unrelated config files?

---

## Non-goals

This is intentionally **not** an Omarchy clone.

Do not initially build:

- a generic desktop theming framework
- theme installation from remote repositories
- theme previews
- wallpaper handling
- Wofi and Hyprland integration
- automatic theme conversion
- complex validation
- compatibility with arbitrary applications
- a sophisticated templating engine

The implementation should stay small and understandable.

---

## Core idea

Keep application configuration separate from theme configuration.

Each application's normal config references a stable `current` theme path.

Static packs are Stow-managed, while the selected theme is runtime state:

```text
~/.local/share/dotfiles/themes/
├── gruvbox/
│   ├── foot.ini
│   ├── tmux.conf
│   ├── nvim.lua
│   └── waybar.css
└── everforest/
    ├── foot.ini
    ├── tmux.conf
    ├── nvim.lua
    └── waybar.css

~/.local/state/dotfiles/theme/
└── current -> ~/.local/share/dotfiles/themes/everforest
```

Switching theme changes only the local `current` symlink:

```text
~/.local/state/dotfiles/theme/current -> ~/.local/share/dotfiles/themes/gruvbox
```

Applications always reference files through the runtime `current` path. This
keeps theme selection out of the Git worktree.

---

## Application integration

### Foot

Normal Foot configuration:

```ini
# ~/.config/foot/foot.ini

include=~/.local/state/dotfiles/theme/current/foot.ini

font=JetBrainsMono Nerd Font:size=11
pad=8x8
```

The theme file contains only theme-specific configuration:

```ini
# ~/.local/share/dotfiles/themes/gruvbox/foot.ini

[colors-dark]
background=282828
foreground=ebdbb2
regular0=3c3836
regular1=cc241d
regular2=98971a
regular3=d79921
regular4=458588
```

---

### tmux

Normal tmux configuration:

```tmux
# ~/.tmux.conf

# General tmux configuration...

source-file ~/.local/state/dotfiles/theme/current/tmux.conf
```

Theme file:

```tmux
# ~/.local/share/dotfiles/themes/gruvbox/tmux.conf

set -g status-style "bg=#282828,fg=#ebdbb2"
set -g pane-active-border-style "fg=#a89984"
```

Reloading the theme can initially be done with:

```bash
tmux source-file ~/.tmux.conf
```

---

### Neovim

Normal Neovim configuration:

```lua
dofile(vim.fn.expand("~/.local/state/dotfiles/theme/current/nvim.lua"))
```

Theme file:

```lua
-- ~/.local/share/dotfiles/themes/gruvbox/nvim.lua

vim.cmd.colorscheme("gruvbox")
```

For the first POC it is acceptable if existing Neovim instances do not automatically change theme.

A new Neovim instance reading the correct theme is enough to validate the architecture.

---

### Waybar

The layout and spacing rules stay in `waybar/.config/waybar/style.css`, which
imports only the palette from the selected theme:

```css
/* ~/.config/waybar/style.css */

@import url("../../.local/state/dotfiles/theme/current/waybar.css");
```

The relative import resolves against the stylesheet location, so no home path
is hardcoded. Each theme pack owns the Waybar `@define-color` palette:

```css
/* ~/.local/share/dotfiles/themes/gruvbox/waybar.css */

@define-color background #282828;
@define-color accent #7daea3;
```

Waybar reloads on `SIGUSR2`, so `theme-set` repaints the running bar without a
restart.

---

## Minimal `theme-set` command

The Stow-managed `themes/.local/bin/theme-set` script validates a theme name,
repoints the runtime `current` symlink, reloads tmux when a server is running,
and sends `SIGUSR2` to Waybar when one is running. Run without an argument, it
prints the active theme. `make stow` initializes the selection to Everforest
only when no valid selection exists.

Usage:

```bash
theme-set gruvbox
theme-set everforest
theme-set            # prints the active theme
```

---

## First success criterion

The POC is successful if:

1. Foot, tmux, Neovim, and Waybar read their theme configuration from one stable `current` path.
2. `theme-set <name>` changes that path.
3. tmux and Waybar update immediately.
4. New Foot and Neovim instances use the newly selected theme.
5. No application-specific theme paths have to be remembered during normal use.

Live reloading everything is explicitly **not required** for the first version.

---

## Design principle

Prefer the smallest abstraction that removes the real inconvenience.

Start with:

```text
theme directory
      +
current symlink
      +
small switch script
```

Only add:

- templates
- generated files
- reload adapters
- IPC
- watchers

when there is a concrete reason.

The goal is not maximum automation.

The goal is:

> One understandable mechanism that removes the need to manually remember and edit several application-specific theme configurations.

---

## Relationship to Omarchy

Omarchy can be treated as a reference implementation rather than as a dependency.

Useful ideas to inspect and selectively borrow:

- semantic theme palettes
- generated application-specific configs
- stable `current/theme` paths
- atomic theme switching
- application-specific reload hooks
- Foot OSC color updates

The POC should deliberately remain much smaller because it only needs to support one machine and a few known applications.

---

## Investigation checklist

- [x] Create the Gruvbox theme pack
- [x] Create the Everforest theme pack
- [x] Add Foot theme fragments
- [x] Add tmux theme fragments
- [x] Add Neovim theme fragments
- [x] Add Waybar palette fragments
- [x] Keep the `current` symlink in local runtime state
- [x] Update Foot config to include `current/foot.ini`
- [x] Update tmux config to source `current/tmux.conf`
- [x] Update Neovim config to load `current/nvim.lua`
- [x] Update Waybar config to import `current/waybar.css`
- [x] Implement minimal `theme-set`
- [x] Verify tmux reload
- [x] Verify Waybar reload
- [x] Verify new Foot instances
- [x] Verify new Neovim instances

---

## Keep in mind

If the POC starts accumulating:

- plugin systems
- manifests
- schema validation
- generic application discovery
- complex fallback logic

stop and reconsider the scope.

For this project, being able to read the entire implementation in a few minutes is a feature.
