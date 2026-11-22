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
local screenshot_monitor = [[
mkdir -p "$HOME/Pictures/Screenshots" &&
file="$HOME/Pictures/Screenshots/Screenshot_$(date +%Y-%m-%d_%H-%M-%S).png" &&
grim -o "$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')" "$file" &&
wl-copy --type image/png < "$file" &&
notify-send -t 2000 "Screenshot saved" "${file##*/}"
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

hl.on("hyprland.start", function()
  hl.exec_cmd(
    "systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR && systemctl --user start hyprland-session.target")
  hl.exec_cmd("mako")
  hl.exec_cmd("lxqt-policykit-agent")
  hl.exec_cmd("waybar")
  hl.exec_cmd("playerctld daemon")
end)

hl.on("hyprland.shutdown", function()
  os.execute("systemctl --user stop hyprland-session.target && sleep 0.1")
end)

-- Every bind carries a description; `keybinds` (SUPER+F1) lists them.
local function bind(keys, action, description, opts)
  opts = opts or {}
  opts.description = description
  hl.bind(keys, action, opts)
end

bind(main_mod .. " + Return", hl.dsp.exec_cmd(terminal), "Terminal")
bind(main_mod .. " + D", hl.dsp.exec_cmd(menu), "App launcher")
bind(main_mod .. " + Q", hl.dsp.window.close(), "Close window")
bind(main_mod .. " + CTRL + Q", hl.dsp.exec_cmd(confirm_exit), "Exit Hyprland")
bind(main_mod .. " + F", hl.dsp.window.fullscreen({ action = "toggle" }), "Fullscreen")
bind(main_mod .. " + SPACE", hl.dsp.window.float({ action = "toggle" }), "Toggle floating")
bind(main_mod .. " + V", hl.dsp.exec_cmd(clipboard_history), "Clipboard history")
bind(main_mod .. " + S", hl.dsp.exec_cmd("snippet-type"), "Snippet picker")
bind(main_mod .. " + F1", hl.dsp.exec_cmd("keybinds"), "Show keybinds")
bind("Print", hl.dsp.exec_cmd(screenshot), "Screenshot to clipboard")
bind("SHIFT + Print", hl.dsp.exec_cmd(screenshot_monitor), "Screenshot focused monitor to clipboard")

-- Apps live on the SUPER+SHIFT layer.
bind(main_mod .. " + SHIFT + B", hl.dsp.exec_cmd("firefox --new-window"), "Firefox")
bind(main_mod .. " + SHIFT + F", hl.dsp.exec_cmd("nautilus --new-window"), "Files")
bind(main_mod .. " + SHIFT + M", hl.dsp.workspace.toggle_special("music"), "Music")

bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), "Play/pause")
bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), "Next track")
bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), "Previous track")

bind(main_mod .. " + H", hl.dsp.focus({ direction = "l" }), "Focus left")
bind(main_mod .. " + J", hl.dsp.focus({ direction = "d" }), "Focus down")
bind(main_mod .. " + K", hl.dsp.focus({ direction = "u" }), "Focus up")
bind(main_mod .. " + L", hl.dsp.focus({ direction = "r" }), "Focus right")
bind(main_mod .. " + SHIFT + H", hl.dsp.window.move({ direction = "l" }), "Move window left")
bind(main_mod .. " + SHIFT + J", hl.dsp.window.move({ direction = "d" }), "Move window down")
bind(main_mod .. " + SHIFT + K", hl.dsp.window.move({ direction = "u" }), "Move window up")
bind(main_mod .. " + SHIFT + L", hl.dsp.window.move({ direction = "r" }), "Move window right")

bind(main_mod .. " + mouse:272", hl.dsp.window.drag(), "Drag window", { mouse = true })
bind(main_mod .. " + mouse:273", hl.dsp.window.resize(), "Resize window", { mouse = true })
bind(main_mod .. " + CTRL + Left", hl.dsp.window.resize({ x = -20, y = 0, relative = true }), "Resize left", { repeating = true })
bind(main_mod .. " + CTRL + Right", hl.dsp.window.resize({ x = 20, y = 0, relative = true }), "Resize right", { repeating = true })
bind(main_mod .. " + CTRL + Up", hl.dsp.window.resize({ x = 0, y = -20, relative = true }), "Resize up", { repeating = true })
bind(main_mod .. " + CTRL + Down", hl.dsp.window.resize({ x = 0, y = 20, relative = true }), "Resize down", { repeating = true })
bind(main_mod .. " + CTRL + equal", hl.dsp.layout("splitratio 1 exact"), "Reset split ratio")

for workspace = 1, 4 do
  bind(main_mod .. " + " .. workspace, hl.dsp.focus({ workspace = workspace }), "Workspace " .. workspace)
  bind(main_mod .. " + SHIFT + " .. workspace, hl.dsp.window.move({ workspace = workspace }), "Move window to workspace " .. workspace)
end

bind(main_mod .. " + CTRL + H", hl.dsp.workspace.move({ monitor = "l" }), "Move workspace to left monitor")
bind(main_mod .. " + CTRL + L", hl.dsp.workspace.move({ monitor = "r" }), "Move workspace to right monitor")

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
    kb_model = "pc105",
    kb_variant = "us",
    kb_file = os.getenv("HOME") .. "/.config/hypr/keyboard.xkb",
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
