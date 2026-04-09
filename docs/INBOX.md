# INBOX

Triage intake for this repository. Items here have been scoped to this repo and are ready to act on.

Process each item: implement it, move it to `docs/BACKLOG.md` if deferred, or discard it. Keep this file clear.

---

## Vim `*` register clipboard broken

`clip.exe` is not executable on Linux — Neovim throws `E475: Invalid value for argument cmd`. Configure the correct clipboard provider for Linux/Wayland: `wl-clipboard` (`wl-copy`/`wl-paste`).

## Kitty font missing Nerd Font glyphs

`kitty.conf` uses plain JetBrains Mono which lacks Nerd Font glyph ranges; Neovim file explorer shows broken symbols. Install JetBrainsMono Nerd Font from https://github.com/ryanoasis/nerd-fonts/releases and update `kitty.conf`:

```
font_family JetBrainsMono Nerd Font
```
