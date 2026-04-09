# Backlog

Ideas and potential features. Not prioritized or scheduled.

## Active

## Deferred

### Clipboard history with `cliphist`

Add Wayland clipboard history via `cliphist`. Run `wl-paste --watch cliphist store` as a background service (systemd user unit or compositor autostart). Bind a key to `cliphist list | fzf | cliphist decode | wl-copy` for fuzzy history picker.

### `--tiny` profile
Minimal install for servers, VPS, Raspberry Pi. vim, tmux, zsh aliases only.
See [docs/plans/tiny-profile.md](plans/tiny-profile.md) for full design.

## Done

### Vim `*` register clipboard broken

Configured `wl-clipboard` (`wl-copy`/`wl-paste`) for Linux/Wayland in both Neovim (`init.lua`) and tmux (`.tmux.conf`). WSL path unchanged.

### Kitty font missing Nerd Font glyphs

`kitty.conf` uses plain JetBrains Mono which lacks Nerd Font glyph ranges; Neovim file explorer shows broken symbols. Install JetBrainsMono Nerd Font from https://github.com/ryanoasis/nerd-fonts/releases and update `kitty.conf`:

```
font_family JetBrainsMono Nerd Font
```

