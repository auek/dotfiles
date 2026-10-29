#!/usr/bin/env python3
"""Smoke-test the real stowed work profile; requires nvim, stow, and Python 3.

Usage: python3 scripts/test-nvim-work.py /absolute/path/to/nvim [plugin-fixtures]
All HOME/XDG state and clipboard processes are disposable fixtures.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NVIM = str(Path(shutil.which(sys.argv[1] if len(sys.argv) > 1 else "nvim")).resolve())
STOW = shutil.which("stow")


def run(args, env):
    result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=30, cwd=env.get("HOME"))
    assert result.returncode == 0, result.stdout + result.stderr
    # Neovim can print Lua/startup errors yet exit zero after :qa!.
    assert "Error" not in result.stderr, result.stderr
    return result


with tempfile.TemporaryDirectory(prefix="nvim-work-check-") as tmp:
    base = Path(tmp)
    # Copy only this package: the unstowed home configuration cannot be borrowed.
    packages = base / "arbitrary checkout" / "packages"
    shutil.copytree(ROOT / "packages/nvim-work", packages / "nvim-work")
    scenarios = ["native", "wsl-missing", "wsl"]
    if len(sys.argv) > 2:
        scenarios.append("native-plugins")
    for scenario in scenarios:
        home = base / scenario
        home.mkdir()
        bin_dir = home / "bin"
        bin_dir.mkdir()
        env = {**os.environ, "HOME": str(home), "PATH": str(bin_dir),
               "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_DATA_HOME": str(home / ".data"),
               "XDG_STATE_HOME": str(home / ".state"),
               "XDG_CACHE_HOME": str(home / ".cache"),
               "SCENARIO": scenario}
        if scenario == "native-plugins":
            shutil.copytree(Path(sys.argv[2]), home / ".data/nvim/nvim-work/lazy")
            env["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
            for name in ("everforest", "gruvbox"):
                theme = home / ".local/state/dotfiles/theme" / name
                theme.mkdir(parents=True)
                shutil.copy(ROOT / "packages/themes/.local/share/dotfiles/themes" / name / "nvim.lua",
                            theme / "nvim.lua")
        env.pop("NVIM_APPNAME", None)
        env.pop("VIMINIT", None)
        env.pop("EXINIT", None)
        if scenario != "wsl-missing":
            mock = bin_dir / "powershell.exe"
            mock.write_text(f"#!{sys.executable}\n" + '''import os, pathlib, sys, json
home = pathlib.Path(os.environ["HOME"])
with (home / "calls").open("a") as f: f.write(json.dumps(sys.argv[1:]) + "\\n")
if "Set-Clipboard" in sys.argv[-1]:
    (home / "copied").write_bytes(sys.stdin.buffer.read())
else:
    sys.stdout.buffer.write((home / "paste").read_bytes())
''')
            mock.chmod(0o755)
        (home / "unrelated").write_text("preserve me")
        run([STOW, "--no-folding", f"--dir={packages}", f"--target={home}", "nvim-work"],
            {**os.environ})
        before = home / "before.lua"
        before.write_text('''local has = vim.fn.has
vim.fn.has = function(feature)
  if feature == "wsl" then return os.getenv("SCENARIO"):match("^native") and 0 or 1 end
  return has(feature)
end
_G.real_system = vim.system
_G.real_spawn = vim.uv.spawn
_G.real_jobstart = vim.fn.jobstart
local function forbidden() error("Unexpected startup subprocess") end
vim.system = forbidden
vim.fn.system = forbidden
vim.fn.systemlist = forbidden
vim.fn.jobstart = forbidden
vim.uv.spawn = forbidden
''')
        checks = home / "checks.lua"
        checks.write_text(r'''
local function read(path) return vim.fn.readfile(path, "b") end
assert(vim.g.mapleader == " " and vim.o.clipboard == "")
assert(vim.g.colors_name == (vim.env.SCENARIO == "native-plugins" and "everforest" or "habamax"))
assert(not package.loaded["mason"] and not package.loaded["telescope.builtin"])
if vim.env.SCENARIO ~= "native-plugins" then
  assert(not package.loaded.lazy)
  local notifications = {}
  local notify = vim.notify
  vim.notify = function(message) table.insert(notifications, message) end
  vim.fn.maparg(" ff", "n", false, true).callback()
  assert(notifications[1]:find(":Lazy", 1, true))
  vim.notify = notify
end
assert(vim.fn.filereadable(vim.env.HOME .. "/calls") == 0)
if vim.env.SCENARIO == "wsl" then
  assert(vim.g.clipboard.name == "WSL Windows clipboard")
  vim.system = _G.real_system
  vim.uv.spawn = _G.real_spawn
  vim.api.nvim_buf_set_lines(0, 0, -1, false, {"ordinary yank"})
  vim.cmd.normal({args = {"yy"}, bang = true})
  assert(vim.fn.filereadable(vim.env.HOME .. "/calls") == 0)
  vim.bo.modified = false
  local clipboard = vim.g.clipboard
  local lines = {[[åäö 'quotes' "double" \ slash; $(not-code)]], "second line"}
  for _, reg in ipairs({ "+", "*" }) do
    clipboard.copy[reg](vim.list_extend(vim.deepcopy(lines), {""}), "V")
    assert(table.concat(read(vim.env.HOME .. "/copied"), "\n") == table.concat(lines, "\n") .. "\n")
    vim.fn.writefile({"åäö\r", "second\r", ""}, vim.env.HOME .. "/paste", "b")
    local result = clipboard.paste[reg]()
    assert(vim.deep_equal(result, {{"åäö", "second", ""}, "v"}))
    clipboard.copy[reg]({""}, "v")
    assert(table.concat(read(vim.env.HOME .. "/copied"), "\n") == "")
    vim.fn.writefile({}, vim.env.HOME .. "/paste", "b")
    assert(vim.deep_equal(clipboard.paste[reg](), {{""}, "v"}))
  end
  -- Exercise Neovim's provider dispatch, not just the callback functions.
  vim.fn.setreg("+", lines, "V")
  assert(table.concat(read(vim.env.HOME .. "/copied"), "\n") == table.concat(lines, "\n") .. "\n", vim.inspect(read(vim.env.HOME .. "/copied")))
  vim.fn.writefile({"provider\r", "paste"}, vim.env.HOME .. "/paste", "b")
  assert(vim.deep_equal(vim.fn.getreg("*", 1, true), {"provider", "paste"}))
  local calls = vim.fn.readfile(vim.env.HOME .. "/calls")
  for _, call in ipairs(calls) do
    local args = vim.json.decode(call)
    assert(args[1] == "-NoLogo" and args[4] == "-Command" and #args == 5)
    assert(not args[5]:find("åäö", 1, true))
  end
else
  assert(vim.g.clipboard == nil)
end
if vim.env.SCENARIO == "native-plugins" then
  assert(package.loaded.lazy)
  assert(vim.fn.exists(":Lazy") == 2 and vim.fn.exists(":WorkPluginsInstall") == 0)
  local config = require("lazy.core.config")
  local isolated = vim.fn.stdpath("state") .. "/nvim-work/"
  for _, path in ipairs({config.options.lockfile, config.options.state,
      config.options.pkg.cache, config.options.readme.root}) do
    assert(path:sub(1, #isolated) == isolated, path)
  end
  assert(config.options.root == vim.fn.stdpath("data") .. "/nvim-work/lazy")
  assert(config.options.local_spec == false)
  vim.system = _G.real_system
  vim.uv.spawn = _G.real_spawn
  vim.fn.jobstart = _G.real_jobstart
  local project = vim.env.HOME .. "/project"
  vim.fn.mkdir(project .. "/.git", "p")
  vim.fn.writefile({"needle in code"}, project .. "/code.txt")
  vim.fn.writefile({"needle hidden"}, project .. "/.hidden")
  vim.fn.writefile({"ignored.txt"}, project .. "/.ignore")
  vim.fn.writefile({"needle ignored"}, project .. "/ignored.txt")
  vim.fn.writefile({"needle metadata"}, project .. "/.git/HEAD")
  vim.cmd.cd(project)
  local function results(key, query)
    vim.fn.maparg(key, "n", false, true).callback()
    local state = require("telescope.actions.state")
    local prompt = vim.api.nvim_get_current_buf()
    local picker = state.get_current_picker(prompt)
    local complete = false
    picker:register_completion_callback(function()
      complete = picker.manager and picker.manager:num_results() >= 2
    end)
    if query then picker:set_prompt(query) end
    assert(vim.wait(5000, function() return complete end))
    local found = {}
    for entry in picker.manager:iter() do found[entry.filename or entry.value] = true end
    require("telescope.actions").close(prompt)
    assert(found["code.txt"] and found[".hidden"], vim.inspect(found))
    assert(not found["ignored.txt"] and not found[".git/HEAD"])
  end
  results(" ff")
  results(" fg", "needle")
  assert(not package.loaded["nvim-tree"])
  vim.cmd.edit(project .. "/code.txt")
  assert(vim.fn.maparg(" fe", "n", false, true).desc == "Toggle file tree")
  vim.cmd.NvimTreeFindFileToggle()
  assert(vim.bo.filetype == "NvimTree")
  local tree = require("nvim-tree.api")
  assert(tree.tree.is_visible())
  local listing = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
  assert(listing:find("code.txt", 1, true) and listing:find(".hidden", 1, true), listing)
  assert(not listing:find("HEAD", 1, true))
  tree.tree.close()
  assert(not tree.tree.is_visible())
  local themes = vim.env.HOME .. "/.local/state/dotfiles/theme/"
  assert(vim.g.colors_name == "everforest") -- no selection exists yet
  assert(vim.uv.fs_symlink(themes .. "gruvbox", themes .. "current"))
  vim.api.nvim_exec_autocmds("FocusGained", {})
  assert(vim.g.colors_name == "gruvbox" and vim.g.dotfiles_theme == "gruvbox")
  assert(vim.uv.fs_unlink(themes .. "current"))
  assert(vim.uv.fs_symlink(themes .. "everforest", themes .. "current"))
  vim.cmd.ReloadTheme()
  assert(vim.g.colors_name == "everforest")
  local theme_count = #vim.api.nvim_get_autocmds({group = "NvimWorkThemeReload"})
  require("work.theme").setup()
  assert(#vim.api.nvim_get_autocmds({group = "NvimWorkThemeReload"}) == theme_count)
  local executable = vim.fn.executable
  vim.fn.executable = function(cmd) return cmd == "rg" and 0 or executable(cmd) end
  local warning
  local notify = vim.notify
  vim.notify = function(message) warning = message end
  vim.fn.maparg(" fg", "n", false, true).callback()
  assert(warning:find("requires ripgrep"))
  vim.notify = notify
  vim.fn.executable = executable
end
local path = vim.env.HOME .. "/external.txt"
vim.fn.writefile({"original"}, path)
vim.cmd.edit(path)
vim.fn.writefile({"external longer"}, path)
vim.api.nvim_exec_autocmds("FocusGained", {})
assert(vim.api.nvim_get_current_line() == "external longer" and not vim.bo.modified)
-- Defer while inserting or editing a command, then reload on a safe event.
local mode = vim.fn.mode
for _, blocked in ipairs({"i", "c"}) do
  vim.fn.writefile({"deferred " .. blocked}, path)
  vim.fn.mode = function() return blocked end
  vim.api.nvim_exec_autocmds("FocusGained", {})
  assert(vim.api.nvim_get_current_line() ~= "deferred " .. blocked)
  vim.fn.mode = mode
  vim.api.nvim_exec_autocmds("CursorHold", {})
  assert(vim.api.nvim_get_current_line() == "deferred " .. blocked)
end
vim.api.nvim_buf_set_lines(0, 0, -1, false, {"unsaved"})
vim.fn.writefile({"external newer still"}, path)
vim.api.nvim_exec_autocmds("BufEnter", {})
assert(vim.api.nvim_get_current_line() == "unsaved" and vim.bo.modified)
local close = vim.fn.maparg(" b", "n", false, true).callback
local buf = vim.api.nvim_get_current_buf()
close()
assert(vim.api.nvim_get_current_buf() == buf and vim.bo.modified)
assert(not pcall(vim.cmd, "quit"))
vim.bo.modified = false -- fixture only: allow testing closing a clean buffer
vim.cmd.vsplit()
close()
assert(#vim.api.nvim_list_wins() == 2 and not vim.api.nvim_buf_is_valid(buf))
local count = #vim.api.nvim_get_autocmds({group = "NvimWorkReload"})
dofile(vim.fn.stdpath("config") .. "/init.lua")
assert(#vim.api.nvim_get_autocmds({group = "NvimWorkReload"}) == count)
if vim.env.SCENARIO == "native-plugins" then assert(vim.g.colors_name == "everforest") end
''')
        result = run([NVIM, "--headless", "-i", "NONE", "--cmd", f"luafile {before}",
                      "-c", f"luafile {checks}", "-c", "qa!"], env)
        if scenario == "native-plugins":
            selection = home / ".local/state/dotfiles/theme/current"
            selection.unlink()
            selection.symlink_to(selection.parent / "gruvbox", target_is_directory=True)
            run([NVIM, "--headless", "-i", "NONE", "--cmd", f"luafile {before}",
                 "-c", 'lua assert(vim.g.colors_name == "gruvbox")', "-c", "qa!"], env)
        run([STOW, "--delete", "--no-folding", f"--dir={packages}", f"--target={home}",
             "nvim-work"], {**os.environ})
        assert not (home / ".config/nvim/init.lua").exists()
        assert (home / "unrelated").read_text() == "preserve me"
        assert (packages / "nvim-work/.config/nvim/init.lua").read_bytes() == (
            ROOT / "packages/nvim-work/.config/nvim/init.lua").read_bytes()
        print(f"PASS: {scenario}: startup, clipboard, safe reload, buffer close, unstow")
        if scenario == "native-plugins":
            print("PASS: Telescope search, nvim-tree, Everforest default, theme selection/reload")
print(run([NVIM, "--version"], os.environ).stdout.splitlines()[0])
