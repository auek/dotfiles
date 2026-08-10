# Hyprland Setup (Fedora)

This is the current manual setup for the Fedora Hyprland workstation. Hyprland
packages are deliberately not installed by `setup.sh`; a future opt-in
`--hyprland` profile can automate this list once its scope is defined.

## Install packages

Enable the COPR that supplies the current Hyprland stack, then install the core
components:

```bash
sudo dnf copr enable ashbuk/Hyprland-Fedora
sudo dnf install hyprland hypridle xdg-desktop-portal-hyprland
```

Install the session utilities used by the Stow-managed configuration:

```bash
sudo dnf install mako lxpolkit wofi swaybg grim slurp wl-clipboard
```

| Package | Purpose |
|---|---|
| `hyprland` | Wayland compositor |
| `hypridle` | Turns displays off and suspends the system after inactivity |
| `xdg-desktop-portal-hyprland` | Desktop portal backend for Hyprland |
| `mako` | Notification daemon |
| `lxpolkit` | Polkit authentication agent |
| `wofi` | Application launcher |
| `swaybg` | Wallpaper renderer |
| `grim`, `slurp`, `wl-clipboard` | Cropped screenshots saved to disk and copied to the clipboard |

`hyprlock` is intentionally not configured. The idle policy turns displays off
and suspends the machine; it does not lock the session.

## Load the dotfiles configuration

The Stow-managed configuration lives in
`~/.config/hypr/dotfiles.lua`. Keep the primary Hyprland configuration as a
regular local file so Hyprland cannot create a fallback file inside the Git
worktree:

```lua
require("dotfiles")
```

Save this as `~/.config/hypr/hyprland.lua`.

## Local assets and key bindings

Place a local wallpaper at `~/Pictures/Wallpapers/current.jpg`. It is loaded by
`swaybg` with fill mode and is intentionally not stored in this public
repository.

The screenshot binding is `Print`. Drag to select a region; the resulting PNG
is saved to `~/Pictures/Screenshots/` and copied to the Wayland clipboard.

In OpenCode, use `Ctrl+V` to attach the image. `Ctrl+Shift+V` is Kitty's text
paste shortcut and cannot attach a PNG to a terminal application.

## Tmux across compositor changes

When a tmux server survives a switch between GNOME and Hyprland, it can retain
the previous `WAYLAND_DISPLAY` socket. Add the current Wayland environment when
attaching to tmux rather than hardcoding a socket name:

```tmux
set -ga update-environment " WAYLAND_DISPLAY XDG_RUNTIME_DIR"
```

Restarting the tmux server from the current graphical session also refreshes
these variables.
