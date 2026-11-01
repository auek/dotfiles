#!/usr/bin/env python3
"""Smoke-test the shared stowed profile; requires nvim, stow, and Python 3.

Usage: python3 scripts/test-nvim.py /absolute/path/to/nvim [plugin-fixtures [mason-fixture|- [parser-fixture]]]
Use --scenario NAME to rerun one failure. The default reports every scenario.
All HOME/XDG state and clipboard processes are disposable fixtures.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ["native", "wsl-missing", "wsl", "local", "invalid-local", "bootstrap-failure", "unrestowed", "native-plugins"]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("nvim", nargs="?", default="nvim")
parser.add_argument("plugins", nargs="?", type=Path)
parser.add_argument("mason", nargs="?", type=Path)
parser.add_argument("parsers", nargs="?", type=Path)
parser.add_argument("--scenario", choices=SCENARIOS)
options = parser.parse_args()
if options.scenario == "native-plugins" and not options.plugins:
    parser.error("native-plugins requires the plugin fixture directory")
NVIM = shutil.which(options.nvim)
STOW = shutil.which("stow")
if not NVIM or not STOW:
    sys.exit("Neovim and GNU Stow must already be installed")
NVIM = str(Path(NVIM).resolve())
if not options.scenario:
    scenarios = SCENARIOS if options.plugins else SCENARIOS[:-1]
    print("Editor scenarios: " + ", ".join(scenarios), flush=True)
    print(f"Coverage: plugins={bool(options.plugins)}, LSP={bool(options.mason and str(options.mason) != '-')}, "
          f"extra parsers={bool(options.parsers)}", flush=True)
    failures = []
    for scenario in scenarios:
        print(f"\n>>> editor: {scenario}", flush=True)
        try:
            result = subprocess.run([sys.executable, __file__, *sys.argv[1:], "--scenario", scenario], timeout=180)
            if result.returncode:
                failures.append(scenario)
        except subprocess.TimeoutExpired:
            failures.append(scenario)
    print(f"Editor: {len(scenarios) - len(failures)}/{len(scenarios)} scenarios passed", flush=True)
    if failures:
        print("Failed scenarios: " + ", ".join(failures), file=sys.stderr)
    sys.exit(bool(failures))


def run(args, env, cwd=None):
    result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=90, cwd=cwd or env.get("HOME"))
    assert result.returncode == 0, result.stdout + result.stderr
    # Neovim can print Lua/startup errors yet exit zero after :qa!.
    lsp_log = Path(env.get("XDG_STATE_HOME", "/tmp")) / "nvim/lsp.log"
    assert "Error" not in result.stderr, result.stderr + (lsp_log.read_text()[:1500] + lsp_log.read_text()[-500:] if lsp_log.exists() else "")
    return result


with tempfile.TemporaryDirectory(prefix="nvim-check-") as tmp:
    base = Path(tmp)
    # Copy only this package: no other package or real user configuration is loaded.
    packages = base / "arbitrary checkout" / "packages"
    shutil.copytree(ROOT / "packages/nvim", packages / "nvim")
    source_snapshot = {path.relative_to(packages): path.read_bytes()
                       for path in packages.rglob("*") if path.is_file()}
    conflict = base / "conflict"
    (conflict / ".config/nvim").mkdir(parents=True)
    ordinary = conflict / ".config/nvim/init.lua"
    ordinary.write_text("-- preserve existing settings\n")
    result = subprocess.run([STOW, "--simulate", "--no-folding", f"--dir={packages}",
                             f"--target={conflict}", "nvim"], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0 and ordinary.read_text() == "-- preserve existing settings\n"
    for scenario in [options.scenario]:
        home = base / scenario
        home.mkdir()
        bin_dir = home / "bin"
        bin_dir.mkdir()
        parent = {key: value for key, value in os.environ.items()
                  if not key.startswith(("MISE_", "__MISE_", "TMUX", "NVIM_", "LUA_"))}
        env = {**parent, "HOME": str(home), "PATH": str(bin_dir),
               "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_DATA_HOME": str(home / ".data"),
               "XDG_STATE_HOME": str(home / ".state"),
               "XDG_CACHE_HOME": str(home / ".cache"),
               "SCENARIO": scenario}
        if scenario == "native-plugins":
            shutil.copytree(options.plugins, home / ".data/nvim/lazy")
            env["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
            if options.mason and str(options.mason) != "-":
                shutil.copytree(options.mason, home / ".data/nvim/mason", symlinks=True)
                env["LSP_FIXTURE"] = "1"
            if options.parsers:
                shutil.copytree(options.parsers, home / ".data/nvim/treesitter-v2")
                env["PARSER_FIXTURE"] = "1"
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
        if scenario == "bootstrap-failure":
            git = bin_dir / "git"
            git.write_text(f"#!{sys.executable}\nimport sys\nprint('simulated clone failure', file=sys.stderr)\nsys.exit(1)\n")
            git.chmod(0o755)
        (home / "unrelated").write_text("preserve me")
        legacy = home / ".data/nvim/nvim-work/keep"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("existing data\n")
        run([STOW, "--no-folding", f"--dir={packages}", f"--target={home}", "nvim"],
            {**os.environ})
        local = home / ".config/nvim/local.lua"
        if scenario == "local":
            local.write_text('return {servers={cssls=false, pyright=true}, parsers={"bash"}, '
                             'features={format_on_save=true}, server_options={pyright={settings={}}}}\n')
        elif scenario == "invalid-local":
            local.write_text('return {parsers={"bash; unsafe"}}\n')
        local_before = local.read_bytes() if local.exists() else None
        run([STOW, "--restow", "--no-folding", f"--dir={packages}", f"--target={home}", "nvim"],
            {**os.environ})
        if scenario == "unrestowed":
            (home / ".config/nvim/lua/config/plugins.lua").unlink()
        mason = home / ".data/nvim/mason"
        installed_before = sorted(path.name for path in (mason / "packages").glob("*"))
        before = home / "before.lua"
        before.write_text('''local has = vim.fn.has
vim.fn.has = function(feature)
  if feature == "wsl" then return os.getenv("SCENARIO"):match("^wsl") and 1 or 0 end
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
if vim.env.SCENARIO == "bootstrap-failure" then
  vim.system = _G.real_system
  vim.uv.spawn = _G.real_spawn
end
''')
        checks = home / "checks.lua"
        checks.write_text(r'''
local function read(path) return vim.fn.readfile(path, "b") end
assert(vim.g.mapleader == " " and vim.o.clipboard == "")
local settings = require("config.settings")
assert(settings.servers.ts_ls and settings.servers.yamlls and settings.servers.bashls)
assert(not settings.features.markdown_preview)
if vim.env.SCENARIO == "local" then
  assert(not settings.servers.cssls and settings.servers.pyright)
  assert(settings.features.format_on_save and vim.deep_equal(settings.parsers, {"bash"}))
else
  assert(settings.servers.cssls and not settings.servers.pyright)
  assert(not settings.features.format_on_save and vim.tbl_contains(settings.parsers, "bash"))
end
assert(vim.g.colors_name == (vim.env.SCENARIO == "native-plugins" and "everforest" or "habamax"))
assert(not package.loaded["telescope.builtin"])
if vim.env.SCENARIO ~= "native-plugins" then assert(not package.loaded["mason"]) end
if vim.env.SCENARIO ~= "native-plugins" then
  assert(not package.loaded.lazy)
  if vim.env.SCENARIO ~= "unrestowed" then
    local notifications = {}
    local notify = vim.notify
    vim.notify = function(message) table.insert(notifications, message) end
    vim.fn.maparg(" ff", "n", false, true).callback()
    assert(notifications[1]:find(":Lazy", 1, true))
    vim.notify = notify
  end
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
  assert(require("mason.settings").current.install_root_dir == vim.fn.stdpath("data") .. "/mason")
  for server, executable in pairs({ts_ls="typescript-language-server", cssls="vscode-css-language-server", yamlls="yaml-language-server", bashls="bash-language-server"}) do
    if vim.fn.executable(executable) == 0 then assert(not vim.lsp.is_enabled(server)) end
    if vim.env.LSP_FIXTURE == "1" then
      assert(vim.fn.executable(executable) == 1, "missing fixture executable: " .. executable)
      assert(vim.lsp.is_enabled(server), "fixture server not enabled: " .. server)
    end
  end
  assert(vim.fn.exists(":Lazy") == 2)
  local config = require("lazy.core.config")
  local isolated = vim.fn.stdpath("state") .. "/dotfiles/"
  for _, path in ipairs({config.options.lockfile, config.options.state,
      config.options.pkg.cache, config.options.readme.root}) do
    assert(path:sub(1, #isolated) == isolated, path)
  end
  assert(config.options.root == vim.fn.stdpath("data") .. "/lazy")
  assert(config.options.local_spec == false)
  assert(config.options.install.missing == true and not config.options.checker.enabled)
  local pins = vim.json.decode(table.concat(vim.fn.readfile(vim.fn.stdpath("config") .. "/lazy-lock.json"), "\n"))
  for name, plugin in pairs(config.plugins) do assert(plugin.commit == pins[name].commit, name) end
  assert(vim.lsp.config.bashls.settings.bashIde.shfmt.path == "")
  assert(not vim.lsp.is_enabled("pyright") and not vim.lsp.is_enabled("lua_ls"))
  vim.system = _G.real_system
  vim.uv.spawn = _G.real_spawn
  vim.fn.jobstart = _G.real_jobstart
  require("lazy").load({plugins={"nvim-cmp"}})
  assert(not package.loaded["nvim-treesitter.configs"] and not package.loaded["nvim-treesitter.query_predicates"])
  assert(not package.loaded["nvim-treesitter.install"], "parser installation must not run at startup")
  local treesitter = require("nvim-treesitter")
  assert(require("nvim-treesitter.config").get_install_dir("parser") == vim.fn.stdpath("data") .. "/treesitter-v2/parser")
  assert(config.plugins["nvim-treesitter"].lazy == false)
  assert(vim.fn.exists(":InstallParsers") == 2)
  local installs = 0
  local install, system, executable, notify = treesitter.install, vim.system, vim.fn.executable, vim.notify
  treesitter.install = function(languages)
    assert(vim.deep_equal(languages, settings.parsers))
    installs = installs + 1
    return {await=function(_, callback) callback(nil, true) end}
  end
  local warning
  vim.notify = function(message) warning = message end
  vim.fn.executable = function(name) return name == "tree-sitter" and 0 or executable(name) end
  vim.cmd.InstallParsers()
  assert(installs == 0 and warning:find("tree%-sitter CLI"))
  vim.fn.executable = function(name) return name == "tree-sitter" and 1 or executable(name) end
  local version = "0.25.10"
  vim.system = function(args)
    assert(vim.deep_equal(args, {"tree-sitter", "--version"}))
    return {wait=function() return {code=0, stdout="tree-sitter " .. version} end}
  end
  vim.cmd.InstallParsers()
  assert(installs == 0 and warning:find("0.26.1"))
  version = "0.27.1"
  vim.cmd.InstallParsers()
  treesitter.install, vim.system, vim.fn.executable, vim.notify = install, system, executable, notify
  assert(installs == 1)
  -- Core hover starts Markdown Treesitter after FileType; a FileType stop hook
  -- did not cover this path. Force injections and conceal-line rendering too.
  local hover, window = vim.lsp.util.open_floating_preview({
    "```typescript", "const answer: number", "```", "Hover documentation",
  }, "markdown", {focus_id="treesitter-regression"})
  local highlighter = vim.treesitter.highlighter.active[hover]
  assert(highlighter, "native Markdown hover highlighter did not start")
  vim.treesitter.get_parser(hover, "markdown"):parse(true)
  vim.api.nvim_win_text_height(window, {})
  vim.cmd.redraw()
  vim.api.nvim_win_close(window, true)
  assert(not vim.tbl_contains(vim.treesitter.query.list_directives(), "set-lang-from-info-string!"))
  print("PASS: Markdown hover with fenced TypeScript, injections and conceal-line rendering")
  local git_project = vim.env.HOME .. "/git-project"
  vim.fn.mkdir(git_project, "p")
  local function git(...)
    local args = {"git", "-C", git_project}
    vim.list_extend(args, {...})
    local result = vim.system(args, {text=true}):wait()
    assert(result.code == 0, result.stderr)
  end
  git("init", "-q")
  vim.fn.writefile({"original"}, git_project .. "/example.sh")
  git("add", "example.sh")
  git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
  vim.cmd.edit(git_project .. "/example.sh")
  assert(vim.wait(5000, function() return vim.b.gitsigns_head ~= nil end), "Git indicators did not attach")
  vim.api.nvim_buf_set_lines(0, 0, -1, false, {"changed", "extra"})
  assert(vim.wait(5000, function()
    local status = vim.b.gitsigns_status_dict
    return status and ((status.changed or 0) > 0 or (status.added or 0) > 0)
  end), "Git indicators did not update")
  vim.bo.modified = false
  local parsed, parser = pcall(vim.treesitter.get_parser, 0, "bash")
  if vim.env.PARSER_FIXTURE == "1" then assert(parsed and parser, "Bash parser fixture did not load") end
  if parsed and vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] then
    assert(vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()])
    print("PASS: real Bash parser and Treesitter highlighting")
  end
  local project = vim.env.HOME .. "/project"
  vim.fn.mkdir(project .. "/.git", "p")
  vim.fn.writefile({"needle in code"}, project .. "/code.txt")
  vim.fn.writefile({"needle hidden"}, project .. "/.hidden")
  vim.fn.writefile({"ignored.txt"}, project .. "/.ignore")
  vim.fn.writefile({"needle ignored"}, project .. "/ignored.txt")
  vim.fn.writefile({"needle metadata"}, project .. "/.git/HEAD")
  vim.cmd.cd(project)
  -- Exercise the asynchronous file-preview path, not only picker result lists.
  -- Telescope 0.1.8 called the removed nvim-treesitter ft_to_lang API here.
  local previews = project .. "/previews"
  vim.fn.mkdir(previews, "p")
  local maker = require("telescope.config").values.buffer_previewer_maker
  for _, case in ipairs({
    {"example.ts", {"export const answer: number = 42;"}, "typescript"},
    {"example.sh", {"#!/usr/bin/env bash", "echo hello"}, "bash"},
    {"example.md", {"```typescript", "const answer: number", "```"}, "markdown"},
    {"example.rs", {"fn main() {}"}, "rust"},
  }) do
    local file, contents, language = previews .. "/" .. case[1], case[2], case[3]
    vim.fn.writefile(contents, file)
    local buffer = vim.api.nvim_create_buf(false, true)
    local utils = require("telescope.utils")
    local has_parser = utils.has_ts_parser
    if language == "rust" then
      utils.has_ts_parser = function(lang) return lang ~= "rust" and has_parser(lang) end
    end
    local completed = false
    maker(file, buffer, {use_ft_detect=true, callback=function() completed = true end})
    assert(vim.wait(5000, function()
      return completed and (vim.treesitter.highlighter.active[buffer] ~= nil or vim.bo[buffer].syntax ~= "")
    end), "file preview/highlighter did not finish: " .. case[1])
    assert(vim.deep_equal(vim.api.nvim_buf_get_lines(buffer, 0, #contents, false), contents), case[1])
    if language == "markdown" or (vim.env.PARSER_FIXTURE == "1" and language ~= "rust") then
      assert(vim.treesitter.highlighter.active[buffer], "no native preview highlighter: " .. case[1])
      vim.treesitter.get_parser(buffer, language):parse(true)
    elseif language == "rust" then
      assert(not vim.treesitter.highlighter.active[buffer] and vim.bo[buffer].syntax == "rust")
    end
    utils.has_ts_parser = has_parser
    vim.api.nvim_buf_delete(buffer, {force=true})
  end
  -- Force a real picker preview window even in the headless terminal's small
  -- default dimensions; previously the preview pane could remain hidden.
  vim.o.columns, vim.o.lines = 180, 55
  require("telescope.builtin").find_files({
    cwd=previews, default_text="example.ts", layout_strategy="horizontal",
    layout_config={horizontal={preview_cutoff=0}},
  })
  local preview_prompt = vim.api.nvim_get_current_buf()
  local preview_picker = require("telescope.actions.state").get_current_picker(preview_prompt)
  assert(vim.wait(5000, function()
    local state = preview_picker.previewer and preview_picker.previewer.state
    return state and state.winid and vim.api.nvim_win_is_valid(state.winid)
      and state.bufnr and vim.api.nvim_buf_is_valid(state.bufnr)
      and vim.api.nvim_buf_get_lines(state.bufnr, 0, 1, false)[1] == "export const answer: number = 42;"
      and (vim.treesitter.highlighter.active[state.bufnr] ~= nil or vim.bo[state.bufnr].syntax ~= "")
  end), "real Telescope picker preview did not render")
  if vim.env.PARSER_FIXTURE == "1" then
    assert(vim.treesitter.highlighter.active[preview_picker.previewer.state.bufnr])
  end
  vim.cmd.redraw()
  require("telescope.actions").close(preview_prompt)
  print("PASS: asynchronous TS/Bash/Markdown previews, missing-parser fallback, and real visible preview pane")
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
    {"foo File", foo_file}, {"missing File", {}}, {"foo !Other", foo_file},
  }) do
    file_complete = false
    file_picker:set_prompt(case[1])
    assert(vim.wait(5000, function() return file_complete end))
    local files = {}
    for entry in file_picker.manager:iter() do table.insert(files, entry.value) end
    table.sort(files)
    assert(vim.deep_equal(files, case[2]), case[1] .. ": " .. vim.inspect(files))
  end
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
  local theme_count = #vim.api.nvim_get_autocmds({group = "DotfilesThemeReload"})
  require("config.theme").setup()
  assert(#vim.api.nvim_get_autocmds({group = "DotfilesThemeReload"}) == theme_count)
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
    [vim.uri_from_fname(vim.fn.stdpath("data") .. "/mason/azure-schema.json")] = "azure-pipelines.yml",
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
  vim.api.nvim_win_set_cursor(0, {1, 10})
  vim.fn.maparg("gh", "n", false, true).callback()
  assert(vim.wait(10000, function()
    local window = vim.b[buf].lsp_floating_preview
    return window and vim.api.nvim_win_is_valid(window)
  end), "gh did not open the TypeScript hover")
  local hover_window = vim.b[buf].lsp_floating_preview
  local hover_buffer = vim.api.nvim_win_get_buf(hover_window)
  assert(vim.treesitter.highlighter.active[hover_buffer])
  vim.treesitter.get_parser(hover_buffer, "markdown"):parse(true)
  vim.api.nvim_win_text_height(hover_window, {})
  vim.api.nvim_win_close(hover_window, true)
  local result = client:request_sync("textDocument/definition", {
    textDocument={uri=vim.uri_from_bufnr(buf)}, position={line=0, character=10},
  }, 10000, buf)
  assert(result and result.result and #result.result > 0, vim.inspect(result))
  local definition = result.result[1]
  assert((definition.uri or definition.targetUri):find("dep.ts", 1, true))
  local completion = client:request_sync("textDocument/completion", {
    textDocument={uri=vim.uri_from_bufnr(buf)}, position={line=2, character=13},
    context={triggerKind=1},
  }, 10000, buf)
  assert(completion and completion.result, vim.inspect(completion))
  local answer = false
  for _, item in ipairs(completion.result.items or completion.result) do
    if item.label == "answer" then answer = true end
  end
  assert(answer, "TypeScript completion did not offer the imported symbol")
  open("test.module.css", "cssls", true)
  open("test.less", "cssls", false)
  open("azure-pipelines.yml", "yamlls", true)
  vim.fn.writefile({"#!/usr/bin/env bash", "echo $undefined_value"}, project .. "/example.sh")
  local _, shell_buf = open("example.sh", "bashls", true)
  assert(vim.wait(15000, function()
    for _, diagnostic in ipairs(vim.diagnostic.get(shell_buf)) do
      if tostring(diagnostic.code):match("^SC") then return true end
    end
    return false
  end), "no ShellCheck diagnostics")
  assert(vim.bo.modified == false)
  for _, active in ipairs(vim.lsp.get_clients()) do active:stop(true) end
  print("PASS: real TS definitions/type diagnostics, CSS/Less, Azure YAML schema and Bash/ShellCheck diagnostics")
end
local path = vim.env.HOME .. "/external.txt"
vim.cmd.enew()
vim.bo.filetype = "markdown"
vim.treesitter.get_parser(0, "markdown"):parse(true)
assert(vim.wo.wrap)
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
local count = #vim.api.nvim_get_autocmds({group = "DotfilesReload"})
dofile(vim.fn.stdpath("config") .. "/init.lua")
assert(#vim.api.nvim_get_autocmds({group = "DotfilesReload"}) == count)
if vim.env.SCENARIO == "native-plugins" then assert(vim.g.colors_name == "everforest") end
''')
        result = run([NVIM, "--headless", "-i", "NONE", "--cmd", f"luafile {before}",
                      "-c", f"luafile {checks}", "-c", "qa!"], env)
        for line in (result.stdout + result.stderr).splitlines():
            if line.startswith("PASS:"):
                print(line)
        if scenario == "bootstrap-failure":
            assert "Lazy bootstrap failed" in result.stderr
            assert not list((home / ".data/nvim/lazy").glob(".lazy-install-*"))
        if scenario == "unrestowed":
            assert "restow the nvim package" in result.stderr
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
            local.write_text('return {servers={cssls=false, pyright=true}, parsers={"bash"}, '
                             'features={format_on_save=true, eslint=true, markdown_preview=true}}\n')
            feature_checks = home / "features.lua"
            feature_checks.write_text('''
local plugins = require("lazy.core.config").plugins
assert(plugins["conform.nvim"] and plugins["nvim-lint"] and plugins["markdown-preview.nvim"])
assert(not require("config.settings").servers.cssls)
assert(not vim.lsp.is_enabled("cssls"))
assert(vim.deep_equal(require("config.settings").parsers, {"bash"}))
require("lazy").load({plugins={"conform.nvim"}})
assert(require("conform").list_formatters_for_buffer ~= nil)
vim.cmd.enew()
vim.bo.filetype = "sh"
local opts = require("lazy.core.plugin").values(plugins["conform.nvim"], "opts", false)
assert(opts.format_on_save(vim.api.nvim_get_current_buf()) == nil)
''')
            run([NVIM, "--headless", "-i", "NONE", "--cmd", f"luafile {before}",
                 "-c", f"luafile {feature_checks}", "-c", "qa!"], env)
            local_before = local.read_bytes()
            # A pull must remain safe before :Lazy update has replaced an
            # installed legacy plugin. Poison scripts/queries must never load.
            plugin = home / ".data/nvim/lazy/nvim-treesitter"
            modern = home / "modern-treesitter"
            plugin.rename(modern)
            (plugin / "lua/nvim-treesitter").mkdir(parents=True)
            (plugin / "lua/nvim-treesitter/configs.lua").write_text("return {}\n")
            (plugin / "plugin").mkdir()
            (plugin / "plugin/legacy.lua").write_text('error("legacy plugin must not load")\n')
            legacy_check = home / "legacy.lua"
            legacy_check.write_text('''
local plugin = require("lazy.core.config").plugins["nvim-treesitter"]
assert(plugin and plugin.lazy and plugin.module == false and not plugin._.loaded)
assert(not package.loaded["nvim-treesitter.query_predicates"])
local buffer, window = vim.lsp.util.open_floating_preview({"```typescript", "const x: number", "```"}, "markdown")
vim.treesitter.get_parser(buffer, "markdown"):parse(true)
vim.api.nvim_win_text_height(window, {})
vim.api.nvim_win_close(window, true)
''')
            run([NVIM, "--headless", "-i", "NONE", "--cmd", f"luafile {before}",
                 "-c", f"luafile {legacy_check}", "-c", "qa!"], env)
            shutil.rmtree(plugin)  # disposable poison fixture, never host data
            modern.rename(plugin)
            print("PASS: legacy installed plugin is disabled safely until explicit update")

        run([STOW, "--delete", "--no-folding", f"--dir={packages}", f"--target={home}",
              "nvim"], {**os.environ})
        assert not (home / ".config/nvim/init.lua").exists()
        assert (local.read_bytes() if local.exists() else None) == local_before
        assert sorted(path.name for path in (mason / "packages").glob("*")) == installed_before
        assert legacy.read_text() == "existing data\n"
        assert (home / "unrelated").read_text() == "preserve me"
        assert (packages / "nvim/.config/nvim/init.lua").read_bytes() == (
            ROOT / "packages/nvim/.config/nvim/init.lua").read_bytes()
        assert {path.relative_to(packages): path.read_bytes()
                for path in packages.rglob("*") if path.is_file()} == source_snapshot
        print(f"PASS: {scenario}: startup, clipboard, safe reload, buffer close, unstow")
        if scenario == "native-plugins":
            print("PASS: completion, Git indicators, parser configuration, optional features, Telescope/tree/themes")
print(run([NVIM, "--version"], os.environ).stdout.splitlines()[0])
