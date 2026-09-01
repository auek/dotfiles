# Hyprland Setup (Fedora 44+)

This is the current manual setup for the Fedora Hyprland workstation. Hyprland
packages are deliberately not installed by `setup.sh`; a future opt-in
`--hyprland` profile can automate this list once its scope is defined. Fedora
44 is the minimum because it packages `cliphist`.

## Install packages

Enable the COPR that supplies the current Hyprland stack, then install the core
components:

```bash
sudo dnf copr enable ashbuk/Hyprland-Fedora
sudo dnf install hyprland hypridle xdg-desktop-portal-hyprland
```

Install the session utilities used by the Stow-managed configuration:

```bash
sudo dnf install foot mako lxpolkit waybar wofi swaybg grim slurp wl-clipboard cliphist
```

| Package | Purpose |
|---|---|
| `hyprland` | Wayland compositor |
| `hypridle` | Turns displays off and suspends the system after inactivity |
| `xdg-desktop-portal-hyprland` | Desktop portal backend for Hyprland |
| `foot` | Default terminal emulator for the Hyprland configuration |
| `mako` | Notification daemon |
| `lxpolkit` | Polkit authentication agent |
| `waybar` | Top status bar with workspaces, window title, audio, network, tray, and clock |
| `wofi` | Application launcher |
| `swaybg` | Wallpaper renderer |
| `grim`, `slurp`, `wl-clipboard` | Cropped screenshots saved to disk and copied to the clipboard |
| `cliphist` | Session-only clipboard history for text and images |

Mako's Stow-managed configuration uses the same Everforest colors, compact
geometry, and urgency states as Waybar and Wofi. It is started automatically by
the Hyprland configuration.

## Install the GTK theme

The `gtk` Stow package selects the external Everforest GTK theme for GTK3 and
GTK4 applications. Install its Fedora build and compatibility dependencies:

```bash
sudo dnf install sassc gtk-murrine-engine
```

The upstream generic requirements mention `gnome-themes-extra`, but Fedora 44
does not publish that package. Its Fedora-specific requirements are the two
packages above.

Clone the theme, fetch its GTK3 parser fix from upstream PR #35, and pin the
reviewed revision:

```bash
mkdir -p ~/.local/src
git clone https://github.com/Fausto-Korpsvart/Everforest-GTK-Theme.git \
  ~/.local/src/Everforest-GTK-Theme
git -C ~/.local/src/Everforest-GTK-Theme fetch origin pull/35/head
git -C ~/.local/src/Everforest-GTK-Theme checkout \
  fede1614cf9a44a03cab25a525f28ff677c1596d
```

The pinned commit differs from upstream `master` only by removing a GTK4-only
`border-spacing` property that otherwise produces GTK3 parser errors.

Install only the dark, compact, green-accent, medium-contrast variant:

```bash
~/.local/src/Everforest-GTK-Theme/themes/install.sh \
  --theme green \
  --color dark \
  --size compact \
  --tweaks medium
```

This creates `~/.themes/Everforest-Green-Dark-Compact-Medium`. The opt-in Stow
package selects it for GTK3 and imports its GTK4 styles for libadwaita without
letting the external installer delete or replace existing GTK4 configuration.
Apply the package and desktop preference only after verifying the theme path:

```bash
make stow-gtk
gsettings set org.gnome.desktop.interface gtk-theme \
  'Everforest-Green-Dark-Compact-Medium'
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
```

Close and reopen GTK applications after changing the theme. Icon and cursor
themes remain at their recorded defaults.

### Theme the Spek Flatpak

Spek is the only installed Flatpak that uses GTK3. Give only that sandbox
read-only access to the exact theme directory and select the theme explicitly:

```bash
flatpak override --user \
  --filesystem="$HOME/.themes/Everforest-Green-Dark-Compact-Medium:ro" \
  --env=GTK_THEME=Everforest-Green-Dark-Compact-Medium \
  cc.spek.Spek
```

The other installed Flatpaks use Qt or Electron and do not need GTK theme
access. Avoid a global `~/.themes` override, which would expose every installed
theme to every Flatpak.

Verify the scoped override and then reopen Spek:

```bash
flatpak override --user --show cc.spek.Spek
flatpak run --command=sh cc.spek.Spek -c \
  'test -r "$HOME/.themes/Everforest-Green-Dark-Compact-Medium/gtk-3.0/gtk.css"'
```

### Roll back the GTK theme

Restore the recorded baseline before removing theme assets:

```bash
flatpak override --user --reset cc.spek.Spek
gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita'
gsettings set org.gnome.desktop.interface color-scheme 'default'
make unstow-gtk
rm -rf \
  ~/.themes/Everforest-Green-Dark-Compact-Medium \
  ~/.themes/Everforest-Green-Dark-Compact-Medium-hdpi \
  ~/.themes/Everforest-Green-Dark-Compact-Medium-xhdpi
```

Only the three exact directories created by this installer variant are removed.
The GTK4 imports disappear with `make unstow-gtk`; no external installer is
allowed to delete GTK4 configuration. Reopen GTK applications afterward.
The recorded baseline had no Spek override, so its app-specific override can be
reset in full. Review it first if unrelated Spek overrides are added later.

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

The `hypr` Stow package also installs `hyprland-session.target`. The Lua
configuration starts this user target with Hyprland and stops it during
shutdown. This activates `graphical-session.target`, which Fedora's desktop
portal services require. The target also starts `cliphist.service`, which
records text and image clipboard data only while Hyprland is running. Its
database is wiped on startup and shutdown. The target additionally starts
`swaybg.service`, which loads the selected theme's wallpaper (see
[Local assets and key bindings](#local-assets-and-key-bindings)). After linking
the package, reload user units once:

```bash
systemctl --user daemon-reload
```

After the next Hyprland login, verify the session and portal services:

```bash
systemctl --user is-active graphical-session.target
gdbus call --session \
  --dest org.freedesktop.portal.Desktop \
  --object-path /org/freedesktop/portal/desktop \
  --method org.freedesktop.DBus.Peer.Ping
systemctl --user is-active xdg-desktop-portal.service
systemctl --user is-active xdg-desktop-portal-hyprland.service
```

## Local assets and key bindings

Place a local wallpaper per theme at
`~/Pictures/Wallpapers/<theme>.<ext>` with `<ext>` one of `.png`, `.jpg`, or
`.jpeg` (for example `everforest.png` or `gruvbox.jpg`). The selected theme's
image is loaded by the `swaybg.service` user unit (via the `swaybg-current`
helper, which resolves `wallpaper-name` against `~/Pictures/Wallpapers`) with
fill mode and is intentionally not stored in this public repository. When no
matching file is present, `swaybg` falls back to the fallback color of the
selected theme (`swaybg-color` in the theme pack). `theme-set` restarts
`swaybg.service` after switching, so the background updates live without
logging out.

The screenshot binding is `Print`. Drag to select a region; the resulting PNG
is saved to `~/Pictures/Screenshots/` and copied to the Wayland clipboard.

The clipboard-history binding is `Super+V`. It opens a fuzzy Wofi picker for
text and image entries; image entries are listed by type and size and restore
the original image when selected. Clipboard history is retained only for the
current Hyprland session. Run `cliphist wipe` to clear it immediately.

In OpenCode, use `Ctrl+V` to attach the image. `Ctrl+Shift+V` is Foot's text
paste shortcut and cannot attach a PNG to a terminal application.

## Tmux across compositor changes

When a tmux server survives a switch between GNOME and Hyprland, it can retain
the previous `WAYLAND_DISPLAY` socket. Add the current Wayland environment when
attaching to tmux rather than hardcoding a socket name:

```tmux
set -ga update-environment " WAYLAND_DISPLAY XDG_RUNTIME_DIR HYPRLAND_INSTANCE_SIGNATURE"
```

Restarting the tmux server from the current graphical session also refreshes
these variables. Existing shells retain their old environment; open a new pane
after reconnecting to use the refreshed values.
