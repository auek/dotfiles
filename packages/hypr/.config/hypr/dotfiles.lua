local terminal = "foot"
local menu = "wofi --show drun"
local main_mod = "SUPER"
local theme_root = os.getenv("HOME") .. "/.local/state/dotfiles/theme/current"
local palette = dofile(theme_root .. "/hyprland.lua")
local screenshot = [[
mkdir -p "$HOME/Pictures/Screenshots" &&
file="$HOME/Pictures/Screenshots/Screenshot_$(date +%Y-%m-%d_%H-%M-%S).png" &&
grim -g "$(slurp -d)" "$file" &&
wl-copy --type image/png < "$file"
]]
local toggle_color_scheme = [[
current="$(gsettings get org.gnome.desktop.interface color-scheme)"
if [ "$current" = "'prefer-dark'" ]; then
  gsettings set org.gnome.desktop.interface color-scheme prefer-light
else
  gsettings set org.gnome.desktop.interface color-scheme prefer-dark
fi
]]
local confirm_exit = [[
choice="$(printf 'Cancel\nExit Hyprland' | wofi --dmenu --prompt 'Exit Hyprland?')"
[ "$choice" = "Exit Hyprland" ] && hyprctl dispatch exit
]]
local clipboard_history = [[
choice="$(cliphist list | wofi --dmenu --prompt 'Clipboard history' --cache-file=/dev/null)"
[ -n "$choice" ] && printf '%s\n' "$choice" | cliphist decode | wl-copy
]]

hl.monitor({
  output = "",
  mode = "preferred",
  position = "auto",
  scale = 1,
})

hl.env("PATH", os.getenv("HOME") .. "/.local/bin:" .. os.getenv("PATH"))
hl.env("LIBVA_DRIVER_NAME", "nvidia")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")

hl.on("hyprland.start", function()
  hl.exec_cmd(
    "systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR && systemctl --user start hyprland-session.target")
  hl.exec_cmd("mako")
  hl.exec_cmd("lxqt-policykit-agent")
  hl.exec_cmd("hypridle")
  hl.exec_cmd("waybar")
end)

hl.on("hyprland.shutdown", function()
  os.execute("systemctl --user stop hyprland-session.target && sleep 0.1")
end)

hl.bind(main_mod .. " + Return", hl.dsp.exec_cmd(terminal))
hl.bind(main_mod .. " + D", hl.dsp.exec_cmd(menu))
hl.bind(main_mod .. " + Q", hl.dsp.window.close())
hl.bind(main_mod .. " + SHIFT + M", hl.dsp.exec_cmd(confirm_exit))
hl.bind(main_mod .. " + SHIFT + F", hl.dsp.exec_cmd("nautilus --new-window"))
hl.bind(main_mod .. " + F", hl.dsp.window.fullscreen({ action = "toggle" }))
hl.bind(main_mod .. " + SPACE", hl.dsp.window.float({ action = "toggle" }))
hl.bind(main_mod .. " + E", hl.dsp.workspace.toggle_special("music"))
hl.bind(main_mod .. " + SHIFT + T", hl.dsp.exec_cmd(toggle_color_scheme))
hl.bind(main_mod .. " + V", hl.dsp.exec_cmd(clipboard_history))
hl.bind("Print", hl.dsp.exec_cmd(screenshot))

hl.bind(main_mod .. " + H", hl.dsp.focus({ direction = "l" }))
hl.bind(main_mod .. " + J", hl.dsp.focus({ direction = "d" }))
hl.bind(main_mod .. " + K", hl.dsp.focus({ direction = "u" }))
hl.bind(main_mod .. " + L", hl.dsp.focus({ direction = "r" }))
hl.bind(main_mod .. " + SHIFT + H", hl.dsp.window.move({ direction = "l" }))
hl.bind(main_mod .. " + SHIFT + J", hl.dsp.window.move({ direction = "d" }))
hl.bind(main_mod .. " + SHIFT + K", hl.dsp.window.move({ direction = "u" }))
hl.bind(main_mod .. " + SHIFT + L", hl.dsp.window.move({ direction = "r" }))

for workspace = 1, 4 do
  hl.bind(main_mod .. " + " .. workspace, hl.dsp.focus({ workspace = workspace }))
  hl.bind(main_mod .. " + SHIFT + " .. workspace, hl.dsp.window.move({ workspace = workspace }))
end

hl.bind(main_mod .. " + CTRL + H", hl.dsp.workspace.move({ monitor = "l" }))
hl.bind(main_mod .. " + CTRL + L", hl.dsp.workspace.move({ monitor = "r" }))

hl.window_rule({
  match = { class = [[^(Spotify|com\.spotify\.Client)$]] },
  workspace = "special:music silent",
})

hl.curve("easeOutQuint", {
  type = "bezier",
  points = { { 0.23, 1 }, { 0.32, 1 } },
})

hl.curve("easeInOutCubic", {
  type = "bezier",
  points = { { 0.65, 0.05 }, { 0.36, 1 } },
})

hl.animation({
  leaf = "windowsIn",
  enabled = true,
  speed = 5,
  bezier = "easeOutQuint",
  style = "popin 90%",
})
hl.animation({
  leaf = "windowsOut",
  enabled = true,
  speed = 4,
  bezier = "easeInOutCubic",
  style = "popin 90%",
})
hl.animation({
  leaf = "windowsMove",
  enabled = true,
  speed = 5,
  bezier = "easeOutQuint",
})
hl.animation({
  leaf = "workspaces",
  enabled = true,
  speed = 4,
  bezier = "easeOutQuint",
  style = "slidefade 15%",
})
hl.animation({ leaf = "fadeIn", enabled = true, speed = 4, bezier = "easeOutQuint" })
hl.animation({ leaf = "fadeOut", enabled = true, speed = 4, bezier = "easeInOutCubic" })

hl.config({
  input = {
    kb_layout = "se",
    kb_variant = "us",
  },
  cursor = {
    hide_on_key_press = true,
    warp_on_change_workspace = 1,
  },
  general = {
    gaps_in = 4,
    gaps_out = 8,
    border_size = 2,
    col = {
      active_border = palette.active_border,
      inactive_border = palette.inactive_border,
    },
  },
  decoration = {
    rounding = 6,
    rounding_power = 2,
    active_opacity = 1.0,
    inactive_opacity = 0.96,
    shadow = {
      enabled = true,
      range = 6,
      render_power = 3,
      color = palette.shadow_color,
    },
    blur = {
      enabled = false,
    },
  },
})
