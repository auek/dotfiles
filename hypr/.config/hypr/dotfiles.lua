local terminal = "kitty"
local menu = "wofi --show drun"
local main_mod = "SUPER"
local wallpaper = os.getenv("HOME") .. "/Pictures/Wallpapers/current.jpg"
local screenshot = [[
mkdir -p "$HOME/Pictures/Screenshots" &&
file="$HOME/Pictures/Screenshots/Screenshot_$(date +%Y-%m-%d_%H-%M-%S).png" &&
grim -g "$(slurp -d)" "$file" &&
wl-copy --type image/png < "$file"
]]

hl.monitor({
    output = "",
    mode = "preferred",
    position = "auto",
    scale = 1,
})

hl.env("LIBVA_DRIVER_NAME", "nvidia")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")

hl.on("hyprland.start", function()
    hl.exec_cmd("mako")
    hl.exec_cmd("lxpolkit")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("swaybg -i " .. wallpaper .. " -m fill")
end)

hl.bind(main_mod .. " + Return", hl.dsp.exec_cmd(terminal))
hl.bind(main_mod .. " + D", hl.dsp.exec_cmd(menu))
hl.bind(main_mod .. " + Q", hl.dsp.window.close())
hl.bind(main_mod .. " + M", hl.dsp.exit())
hl.bind(main_mod .. " + F", hl.dsp.window.fullscreen({ action = "toggle" }))
hl.bind(main_mod .. " + SPACE", hl.dsp.window.float({ action = "toggle" }))
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
    general = {
        gaps_in = 2,
        gaps_out = 2,
        border_size = 0,
    },
})
