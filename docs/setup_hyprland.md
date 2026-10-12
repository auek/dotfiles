# Hyprland Setup (Arch Linux)

The native Arch Hyprland workstation is a supported, opt-in setup target.
Install Arch manually or with `archinstall`, then configure graphics drivers,
networking, audio/Bluetooth support, firmware, and any required boot settings.
These machine-specific prerequisites remain user-managed.

From the repository, run:

```bash
bash setup.sh --full --hyprland
```

`--hyprland` also works with `--slim`. It rejects the server profile, other
distributions, and WSL before installation. Setup installs the package list
below, links the workstation and desktop packages, creates the local Lua
entrypoint if absent, registers user units when possible, and opts into tty1
autostart. It does not start Hyprland or change drivers or boot settings.

## Verification status

- Existing-workstation migration has been smoke-tested: after adding the local
  autostart marker and NVIDIA overrides, exiting Hyprland and logging in again
  produced a working desktop.
- Isolated bootstrap checks and script syntax checks pass.
- **Fresh installation with `setup.sh --hyprland` has not yet been tested.**
  The Arch container installation check has not been run either. Fresh-install
  verification is deferred until the next Arch installation; the migration
  result does not establish that all packages and setup steps work from scratch.

## Install packages

For reference or manual installation, Arch's official repositories provide the
Hyprland stack and session utilities used by the configuration:

```bash
sudo pacman -Syu --needed \
  hyprland hypridle xdg-desktop-portal-hyprland \
  foot mako lxqt-policykit waybar wofi swaybg \
  grim slurp wl-clipboard cliphist nautilus sushi playerctl
```

| Package | Purpose |
|---|---|
| `hyprland` | Wayland compositor |
| `hypridle` | Turns displays off and suspends the system after inactivity |
| `xdg-desktop-portal-hyprland` | Desktop portal backend for Hyprland |
| `foot` | Default terminal emulator for the Hyprland configuration |
| `mako` | Notification daemon |
| `lxqt-policykit` | Polkit authentication agent (`lxqt-policykit-agent`) |
| `waybar` | Top status bar with workspaces, window title, audio, network, tray, and clock |
| `wofi` | Application launcher |
| `swaybg` | Wallpaper renderer |
| `grim`, `slurp`, `wl-clipboard` | Cropped screenshots saved to disk and copied to the clipboard |
| `cliphist` | Session-only clipboard history for text and images |
| `playerctl` | Media-key controls and the `playerctld` daemon for most-recently-active player selection |

Mako's Stow-managed configuration uses the same Everforest colors, compact
geometry, and urgency states as Waybar and Wofi. It is started automatically by
the Hyprland configuration.

## Start after login

With the local opt-in marker created by `setup.sh --hyprland`, the Stow-managed
`.zprofile` runs `start-hyprland` after a local Arch `tty1` login. General setup
and `make stow-hyprland` alone do not enable autostart. It does not run for SSH
sessions, other virtual terminals, or login shells opened inside an existing
graphical session.
Exiting Hyprland returns to the TTY login prompt; use another virtual terminal
for recovery when needed.

Disable autostart by removing the local marker:

```bash
rm ~/.local/state/dotfiles/hyprland/autostart
```

You can still start the desktop manually with `start-hyprland`. Re-running
`setup.sh --hyprland` enables autostart again.

## Install the GTK theme

The `gtk` Stow package selects the external Everforest GTK theme for GTK3 and
GTK4 applications. Install the CSS compiler required by the theme installer:

```bash
sudo pacman -Syu --needed sassc
```

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

Setup creates this file only when absent. Existing files (including symlinks)
are preserved; ensure yours loads `dotfiles` if you want the shared config.

### Hardware-specific overrides

The shared configuration does not select GPU drivers or acceleration backends.
Put settings specific to your machine in the local entrypoint, after
`require("dotfiles")`. Monitor output, mode, and scaling overrides also belong
here; the shared default uses the preferred mode, automatic placement, and
scale 1.

If your NVIDIA setup needs the overrides used by the earlier shared config,
keep them locally:

```lua
require("dotfiles")
hl.env("LIBVA_DRIVER_NAME", "nvidia")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
```

Use these only when appropriate to your installed graphics stack. Setup neither
detects nor installs GPU drivers.

### Existing installations

The former default workstation group included all desktop packages and enabled
Arch tty1 autostart without an explicit preference. Existing desktop links are
not removed by general setup, but new general installs no longer create them.
Use `make stow-hyprland` when maintaining desktop links.

Before the next login or config reload, retain any needed NVIDIA settings in
your local entrypoint as above. To retain tty1 autostart without re-running the
installer, explicitly create its local marker:

```bash
mkdir -p ~/.local/state/dotfiles/hyprland
touch ~/.local/state/dotfiles/hyprland/autostart
```

These are migration commands for you to run when ready; changing the repository
does not itself perform them.

### Session services

The `hypr` Stow package also installs `hyprland-session.target`. The Lua
configuration starts this user target with Hyprland and stops it during
shutdown. This activates `graphical-session.target`, which the desktop portal
services require. The target also starts `cliphist.service` (which
records text and image clipboard data only while Hyprland is running; its
database is wiped on startup and shutdown) and `swaybg.service` (the wallpaper
daemon). After linking the package, reload
user units once:

```bash
systemctl --user daemon-reload
```

Setup attempts this reload without starting services. In a container or a shell
without a user service manager, it reports the deferred command instead.

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
image is loaded by `swaybg` with fill mode and is intentionally not stored in
this public repository. When the file is absent, `swaybg` falls back to the
fallback color of the selected theme (`swaybg-color` in the theme pack).

`swaybg` runs as the session-scoped `swaybg.service` user unit. The unit's
`ExecStart` (`~/.local/bin/swaybg-current`) reads the selected theme's
`wallpaper-name` and `swaybg-color` fragments at start and builds the swaybg
command. The Lua configuration starts the unit together with
`hyprland-session.target` after importing the Wayland environment, and
`theme-set` restarts the unit to switch the background live. The daemon-reload
above registers the unit after linking the package.

The screenshot binding is `Print`. Drag to select a region; the resulting PNG
is saved to `~/Pictures/Screenshots/` and copied to the Wayland clipboard.

`Super+Shift+F` opens Nautilus. It and the Sushi quick previewer are installed
by the package command above. In Nautilus, select an image or supported document
and press `Space` to preview it with Sushi; press `Space` or `Escape` to close
the preview.

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
