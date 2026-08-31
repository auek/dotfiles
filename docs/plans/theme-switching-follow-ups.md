# Theme Switching Follow-ups

Status: later. Retained without a current implementation commitment; the base
theme switcher is complete and archived, and these extensions are not being
worked on yet.

## Goal

Extend the completed theme switcher (Foot, tmux, Neovim, Waybar) so that
switching theme also repaints running applications, and remove color

Baseline: `docs/plans/archive/theme-switching-poc.md` and the `theme-set`
command in the `themes` Stow package.

## Remaining reload work

tmux and Waybar already reload on switch. The two applications that still need

```text
theme-set gruvbox
      │
      ├── update current symlink
      ├── reload tmux            (implemented)
      ├── SIGUSR2 to Waybar      (implemented)
      ├── retint/reload Foot     (this plan)
      └── tell Neovim to reload  (this plan)
```

### Foot

- Can Foot reload an included config file?
- Is restarting Foot necessary?
- Can OSC escape sequences update terminal colors in existing terminals?
- Is Omarchy's OSC approach worth borrowing?

### Neovim

Possible approaches:

- do nothing; only new instances get the new theme
- expose a `:ReloadTheme` command
- use Neovim's remote server/client functionality
- watch the current theme file
- send a command to running instances

Avoid solving this unless it provides useful value.

## Semantic palette

The theme-pack approach duplicates colors between application-specific files:

```text
gruvbox/
├── foot.ini
├── tmux.conf
├── nvim.lua
└── waybar.css
```

Each file may independently contain `#282828`, `#d4be98`, etc.

If this duplication becomes annoying, introduce a semantic palette:

```text
themes/
├── gruvbox.toml
├── everforest.toml
├── catppuccin.toml
└── templates/
    ├── foot.ini.tpl
    ├── tmux.conf.tpl
    ├── nvim.lua.tpl
    └── waybar.css.tpl
```

Example palette:

```toml
background = "#282828"
foreground = "#d4be98"
accent = "#7daea3"

red = "#ea6962"
green = "#a9b665"
yellow = "#d8a657"
blue = "#7daea3"
```

Application templates then translate the semantic palette into each
application's terminology:

```tmux
set -g status-style "bg={{ background }},fg={{ foreground }}"
set -g pane-active-border-style "fg={{ accent }}"
```

```ini
[colors]
background={{ background_strip }}
foreground={{ foreground_strip }}
regular4={{ blue_strip }}
```

Do **not** implement this until the duplication in the simple theme-pack design
becomes an actual problem.

## Possible future scope

Applications excluded by the POC non-goals that could later join the switch:

- Mako
- Wofi
- Hyprland
- wallpaper

Only add an application when the inconvenience is real.

## Keep in mind

Follow the archived POC's design principle: prefer the smallest abstraction
that removes the real inconvenience. Do not add templating engines, IPC,
watchers, or reload adapters without a concrete reason.

For this project, being able to read the entire implementation in a few minutes
is a feature.
