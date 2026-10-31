#!/usr/bin/env python3
"""Smoke-test the real stowed work profile; requires nvim, stow, and Python 3.

Usage: python3 scripts/test-nvim-work.py /absolute/path/to/nvim [plugin-fixtures [mason-fixture]]
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


def run(args, env, cwd=None):
    result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=30, cwd=cwd or env.get("HOME"))
    assert result.returncode == 0, result.stdout + result.stderr
    # Neovim can print Lua/startup errors yet exit zero after :qa!.
    lsp_log = Path(env.get("XDG_STATE_HOME", "/tmp")) / "nvim/lsp.log"
    assert "Error" not in result.stderr, result.stderr + (lsp_log.read_text()[:1500] + lsp_log.read_text()[-500:] if lsp_log.exists() else "")
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
            if len(sys.argv) > 3:
                shutil.copytree(Path(sys.argv[3]), home / ".data/nvim/nvim-work/mason", symlinks=True)
                env["LSP_FIXTURE"] = "1"
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
assert(not package.loaded["telescope.builtin"])
if vim.env.SCENARIO ~= "native-plugins" then assert(not package.loaded["mason"]) end
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
  assert(require("mason.settings").current.install_root_dir == vim.fn.stdpath("data") .. "/nvim-work/mason")
  assert(#require("mason-registry").get_installed_package_names() == (vim.env.LSP_FIXTURE == "1" and 3 or 0))
  for server, executable in pairs({ts_ls="typescript-language-server", cssls="vscode-css-language-server", yamlls="yaml-language-server"}) do
    if vim.fn.executable(executable) == 0 then assert(not vim.lsp.is_enabled(server)) end
  end
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
  for _, app in ipairs({"foo", "bar", "baz", "qux"}) do
    vim.fn.mkdir(project .. "/" .. app .. "-app/src/long/path/to/stuff", "p")
    vim.fn.writefile({"export default null;"}, project .. "/" .. app .. "-app/src/long/path/to/stuff/File.tsx")
  end
  vim.fn.writefile({"export default null;"}, project .. "/foo-app/src/Other.tsx")
  vim.fn.maparg(" ff", "n", false, true).callback()
  local file_prompt = vim.api.nvim_get_current_buf()
  local file_picker = require("telescope.actions.state").get_current_picker(file_prompt)
  local file_complete = false
  file_picker:register_completion_callback(function() file_complete = true end)
  local foo_file = {"foo-app/src/long/path/to/stuff/File.tsx"}
  for _, case in ipairs({
    {"foo", {"foo-app/src/Other.tsx", "foo-app/src/long/path/to/stuff/File.tsx"}},
    {"foo ", {"foo-app/src/Other.tsx", "foo-app/src/long/path/to/stuff/File.tsx"}},
    {"foo F", foo_file}, {"foo Fi", foo_file}, {"foo File", foo_file},
    {"foo Fl", foo_file}, {"missing File", {}}, {"foo long path to", foo_file},
    {"foo !Other", foo_file},
    {"foo", {"foo-app/src/Other.tsx", "foo-app/src/long/path/to/stuff/File.tsx"}},
    {"File foo", foo_file}, {"  foo   File ", foo_file},
    {"baz File", {"baz-app/src/long/path/to/stuff/File.tsx"}},
  }) do
    file_complete = false
    file_picker:set_prompt(case[1])
    assert(vim.wait(5000, function() return file_complete end))
    local files = {}
    for entry in file_picker.manager:iter() do table.insert(files, entry.value) end
    table.sort(files)
    assert(vim.deep_equal(files, case[2]), case[1] .. ": " .. vim.inspect(files))
  end
  local positions = file_picker.sorter:highlighter("foo File", "foo-app/src/long/path/to/stuff/File.tsx")
  table.sort(positions)
  assert(vim.deep_equal(positions, {1,2,3,32,33,34,35}), vim.inspect(positions))
  assert(package.loaded["fzf_lib"] and not package.loaded["work.file_sorter"])
  require("telescope.actions").close(file_prompt)

  -- Outside tmux the navigator still moves between editor splits safely.
  assert(vim.fn.exists(":TmuxNavigateRight") == 2)
  vim.cmd("set splitright | vsplit | wincmd h")
  local left_window = vim.api.nvim_get_current_win()
  vim.cmd.TmuxNavigateRight()
  assert(vim.api.nvim_get_current_win() ~= left_window)
  vim.cmd.TmuxNavigateLeft()
  assert(vim.api.nvim_get_current_win() == left_window)
  vim.cmd.close()
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
if vim.env.LSP_FIXTURE == "1" then
  local project = vim.env.HOME .. "/languages"
  vim.fn.mkdir(project .. "/.git", "p")
  vim.fn.writefile({'{"compilerOptions":{"strict":true}}'}, project .. "/tsconfig.json")
  vim.fn.writefile({'{"name":"fixture"}'}, project .. "/package.json")
  vim.fn.writefile({"export const answer = 42;"}, project .. "/dep.ts")
  vim.fn.writefile({'import { answer } from "./dep";', 'const value: number = "wrong";', "console.log(answer);"}, project .. "/main.ts")
  vim.fn.writefile({"a { color: red; invalid-property: 1; }"}, project .. "/test.module.css")
  vim.fn.writefile({"@color: red;", "a { color: @color; }"}, project .. "/test.less")
  vim.fn.writefile({"trigger: none", "pool: 123", "steps:", "- script: echo hello"}, project .. "/azure-pipelines.yml")
  local yaml = vim.lsp.config.yamlls
  local remote = "https://raw.githubusercontent.com/microsoft/azure-pipelines-vscode/master/service-schema.json"
  assert(yaml.settings.yaml.schemas[remote][1] == "azure-pipelines*.yml")
  assert(yaml.settings.yaml.schemaStore.enable == false)
  -- Same official schema, served from a fixture so this test needs no network.
  yaml.settings.yaml.schemas = {
    [vim.uri_from_fname(vim.fn.stdpath("data") .. "/nvim-work/mason/azure-schema.json")] = "azure-pipelines.yml",
  }
  local function open(file, server, expect_diagnostic)
    vim.cmd.edit(project .. "/" .. file)
    local buf = vim.api.nvim_get_current_buf()
    assert(vim.wait(10000, function() return #vim.lsp.get_clients({bufnr=buf, name=server}) > 0 end), "no client: " .. file)
    local client = vim.lsp.get_clients({bufnr=buf, name=server})[1]
    assert(vim.wait(10000, function() return client.initialized end), "not initialized: " .. file)
    if expect_diagnostic then
      assert(vim.wait(15000, function() return #vim.diagnostic.get(buf) > 0 end), "no diagnostic: " .. file)
    end
    assert(vim.fn.maparg("gd", "n", false, true).buffer == 1)
    return client, buf
  end
  local client, buf = open("main.ts", "ts_ls", true)
  local result = client:request_sync("textDocument/definition", {
    textDocument={uri=vim.uri_from_bufnr(buf)}, position={line=0, character=10},
  }, 10000, buf)
  assert(result and result.result and #result.result > 0, vim.inspect(result))
  local definition = result.result[1]
  assert((definition.uri or definition.targetUri):find("dep.ts", 1, true))
  open("test.module.css", "cssls", true)
  open("test.less", "cssls", false)
  open("azure-pipelines.yml", "yamlls", true)
  assert(vim.bo.modified == false)
  for _, active in ipairs(vim.lsp.get_clients()) do active:stop(true) end
  print("PASS: real TS definition/type diagnostics, CSS Modules diagnostics, Less attachment, Azure YAML schema diagnostics")
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
            directory = home / "directory with spaces"
            directory.mkdir()
            (directory / "example.ts").write_text("export const value = 1;\n")
            check_directory = home / "check-directory.lua"
            check_directory.write_text(r'''assert(vim.wait(3000, function()
  return package.loaded["nvim-tree.api"] and require("nvim-tree.api").tree.is_visible()
end))
assert(vim.bo.filetype == "NvimTree")
assert(vim.g.loaded_netrw == 1 and vim.g.loaded_netrwPlugin == 1)
local listing = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
assert(listing:find("example.ts", 1, true), listing)
''')
            # Exercise real CLI directory startup and :edit before any tree keybinding.
            for args in (["."], [str(directory)], ["-c", "edit " + str(directory).replace(" ", "\\ ")]):
                run([NVIM, "--headless", "-i", "NONE", *args,
                     "-c", f"luafile {check_directory}", "-c", "qa!"], env, cwd=directory)

        run([STOW, "--delete", "--no-folding", f"--dir={packages}", f"--target={home}",
             "nvim-work"], {**os.environ})
        assert not (home / ".config/nvim/init.lua").exists()
        assert (home / "unrelated").read_text() == "preserve me"
        assert (packages / "nvim-work/.config/nvim/init.lua").read_bytes() == (
            ROOT / "packages/nvim-work/.config/nvim/init.lua").read_bytes()
        print(f"PASS: {scenario}: startup, clipboard, safe reload, buffer close, unstow")
        if scenario == "native-plugins":
            print("PASS: Telescope queries, nvim-tree commands/directory startup, theme selection/reload")
            if env.get("LSP_FIXTURE"):
                print("PASS: real TS definition/type diagnostics, CSS diagnostics, Less attachment, Azure schema validation")
print(run([NVIM, "--version"], os.environ).stdout.splitlines()[0])
