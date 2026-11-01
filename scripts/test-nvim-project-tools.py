#!/usr/bin/env python3
"""Test project-local Prettier save hooks and ESLint diagnostics.

Usage: test-nvim-project-tools.py NVIM LAZY CONFORM NVIM_LINT PRETTIER_A PRETTIER_B ESLINT_8 ESLINT_9
Tool arguments are npm fixture prefixes; ESLint fixtures also contain a compatible
@typescript-eslint/parser. Requires Node on PATH. No downloads or real user
configuration changes occur.
"""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) < 9:
    sys.exit(__doc__)
NVIM, LAZY, CONFORM, LINT, *PREFIXES = [Path(arg).resolve() for arg in sys.argv[1:9]]
PRETTIER = [prefix / "node_modules/.bin/prettier" for prefix in PREFIXES[:2]]
ESLINT = [prefix / "node_modules/.bin/eslint" for prefix in PREFIXES[2:]]
VERSIONS = [subprocess.check_output([str(binary), "--version"], text=True).strip()
            for binary in PRETTIER]
if VERSIONS[0] == VERSIONS[1]:
    sys.exit("Supply two different Prettier versions to verify project selection")
ESLINT_VERSIONS = [subprocess.check_output([str(binary), "--version"], text=True).strip() for binary in ESLINT]


class ProjectToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nvim formatting ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.config = self.home / ".config/nvim"
        for module in ("plugins/formatting.lua", "plugins/linting.lua", "config/settings.lua",
                       "config/project_tools.lua", "config/lsp.lua"):
            target = self.config / "lua" / module
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "packages/nvim/.config/nvim/lua" / module, target)
        self.project = self.base / "monorepo with spaces"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        (self.project / "package.json").write_text('{}\n')
        (self.project / ".prettierrc.json").write_text('{"semi":false,"singleQuote":true}\n')
        (self.project / ".editorconfig").write_text('root = true\n[*]\nindent_style = space\nindent_size = 4\n')
        self.install(self.project, 0)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        for name in ("prettier", "eslint", "shfmt", "stylua", "black", "vscode-eslint-language-server"):
            path = self.bin / name
            path.write_text('#!/bin/sh\necho unexpected >> "$HOME/global-tools-called"\nexit 77\n')
            path.chmod(0o755)
        parent = {key: value for key, value in os.environ.items()
                  if not key.startswith(("MISE_", "__MISE_", "NVIM_", "LUA_"))}
        self.env = {**parent, "HOME": str(self.home),
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_DATA_HOME": str(self.home / ".data"),
                    "XDG_STATE_HOME": str(self.home / ".state"),
                    "XDG_CACHE_HOME": str(self.home / ".cache"),
                    "NVIM_LOG_FILE": str(self.home / "nvim.log"),
                    "CONFORM_FIXTURE": str(CONFORM),
                    "LINT_FIXTURE": str(LINT),
                    "PRETTIER_TEST_LOG": str(self.home / "formatter-calls"),
                    "ESLINT_TEST_LOG": str(self.home / "linter-calls"),
                    "PATH": str(self.bin) + os.pathsep + os.environ["PATH"]}
        for key in ("VIMINIT", "EXINIT", "ZDOTDIR"):
            self.env.pop(key, None)

    def install(self, root, index):
        binary = root / "node_modules/.bin/prettier"
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/bin/sh\nprintf "%s\\n" ' + shlex.quote(VERSIONS[index])
                          + ' >> "$PRETTIER_TEST_LOG"\nexec ' + shlex.quote(str(PRETTIER[index])) + ' "$@"\n')
        binary.chmod(0o755)
        return binary

    def case(self, root, filename, filetype, text, index=0, unchanged=False):
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if unchanged:
            expected = text
        else:
            result = subprocess.run([str(PRETTIER[index]), "--stdin-filepath", str(path)],
                                    cwd=root, input=text, text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = result.stdout
            self.assertNotEqual(expected, text, "Fixture must exercise a formatting edit")
        return {"path": str(path), "filetype": filetype, "expected": expected,
                "command": str(root / "node_modules/.bin/prettier")}

    def check(self, cases, enabled=True, missing=False, failure=False, timeout_ms=10000, timeout_error=False):
        if enabled:
            (self.config / "local.lua").write_text(
                'return {features={format_on_save=true},format_timeout_ms=' + str(timeout_ms) + '}\n')
        payload = self.home / "cases.json"
        payload.write_text(json.dumps(cases))
        lua = self.home / "check.lua"
        lua.write_text('''
vim.opt.rtp:prepend(vim.fn.stdpath("config"))
vim.opt.rtp:prepend(vim.env.CONFORM_FIXTURE)
local notices = {}
vim.notify = function(message) table.insert(notices, tostring(message)) end
local function check()
  local spec = require("plugins.formatting")[1]
  local enabled = vim.env.FORMATTING_ENABLED == "1"
  assert(spec.enabled == enabled)
  if enabled then
    spec.opts.log_level = vim.log.levels.DEBUG
    require("conform").setup(spec.opts)
  end
  local cases = vim.json.decode(table.concat(vim.fn.readfile(vim.env.FORMATTING_CASES), "\\n"))
  if enabled then
    -- A competing LSP must never format these buffers, even if available.
    require("conform.lsp_format").get_format_clients = function() return {{}} end
    require("conform.lsp_format").format = function() error("Unexpected LSP fallback") end
  end
  for _, case in ipairs(cases) do
    vim.api.nvim_cmd({cmd="edit", args={case.path}}, {})
    vim.bo.filetype = case.filetype
    if enabled and vim.env.FORMATTING_MISSING ~= "1" and spec.opts.formatters_by_ft[case.filetype] then
      local info = require("conform").get_formatter_info("prettier", 0)
      assert(info.available and info.command == case.command, vim.inspect(info))
      assert(spec.opts.format_on_save(0).lsp_format == "never")
    elseif enabled then
      assert(spec.opts.format_on_save(0) == nil)
    end
    vim.cmd("silent write")
    vim.wait(10, function() return false end)
    local file = assert(io.open(case.path, "rb"))
    local content = file:read("*a"); file:close()
    assert(content == case.expected, case.path .. "\\nExpected: " .. case.expected .. "\\nActual: " .. content)
  end
  if not enabled then assert(not package.loaded.conform) end
  local errors = table.concat(notices, "\\n")
  if vim.env.FORMATTING_FAILURE == "1" then
    assert(errors:find("Formatter failed", 1, true), errors)
  elseif vim.env.FORMATTING_TIMEOUT == "1" then
    assert(errors:find("timeout", 1, true), errors)
  else
    assert(#notices == 0, errors)
  end
end
local ok, err = pcall(check)
if not ok then io.stderr:write(tostring(err) .. "\\n"); vim.cmd("cquit 1") end
vim.cmd("qa!")
''')
        env = {**self.env, "FORMATTING_CASES": str(payload),
               "FORMATTING_ENABLED": "1" if enabled else "0",
               "FORMATTING_MISSING": "1" if missing else "0",
               "FORMATTING_FAILURE": "1" if failure else "0",
               "FORMATTING_TIMEOUT": "1" if timeout_error else "0"}
        # Deliberately unrelated to the edited file; formatter discovery must
        # follow the file, not the current directory or global PATH.
        result = subprocess.run([str(NVIM), "--headless", "-u", "NONE", "-i", "NONE", "-l", str(lua)],
                                cwd=self.project, env=env, capture_output=True, text=True, timeout=60)
        logs = "\n".join(path.read_text() for path in (self.home / ".state").rglob("conform.log"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + logs)
        self.assertFalse((self.home / "global-tools-called").exists())

class FormattingTests(ProjectToolsTests):
    def test_default_off(self):
        self.check([self.case(self.project, "file.ts", "typescript", 'const x="hi";\n', unchanged=True)], enabled=False)
        self.assertFalse((self.home / "formatter-calls").exists())

    def test_supported_filetypes_and_project_config(self):
        examples = [
            ("js", "javascript", 'function f(){return "hi";}\n'),
            ("jsx", "javascriptreact", 'const C=()=> <div/>;\n'),
            ("ts", "typescript", 'const x:string="hi";\n'),
            ("tsx", "typescriptreact", 'const C=()=> <div/>;\n'),
            ("css", "css", '.a{color:red;}\n'),
            ("scss", "scss", '$c:red;.a{color:$c;}\n'),
            ("less", "less", '@c:red;.a{color:@c;}\n'),
            ("json", "json", '{"a":1}\n'),
            ("jsonc", "jsonc", '{"a":1}// comment\n'),
            ("yaml", "yaml", 'items: [1,2]\n'),
            ("html", "html", '<div  class="x"><span>text</span></div>\n'),
            ("md", "markdown", '#   Title\n'),
            ("mdx", "markdown.mdx", '<Button a="b"/>\n'),
            ("graphql", "graphql", 'query{viewer{id}}\n'),
        ]
        cases = [self.case(self.project, "file." + ext, ft, text) for ext, ft, text in examples]
        self.check(cases)
        self.assertEqual((self.home / "formatter-calls").read_text().splitlines(), [VERSIONS[0]] * len(cases))

    def test_nearest_version_and_hoisted_monorepo(self):
        nested = self.project / "apps/nested"
        self.install(nested, 1)
        (nested / "package.json").write_text('{}\n')
        (nested / ".prettierrc.json").write_text('{"semi":true,"singleQuote":false}\n')
        hoisted = self.case(self.project, "apps/hoisted/src/file.ts", "typescript", 'const x="hi";\n')
        local = self.case(nested, "src/file.ts", "typescript", 'const x=\'hi\'\n', index=1)
        self.check([hoisted, local])
        self.assertEqual((self.home / "formatter-calls").read_text().splitlines(), VERSIONS)

    def test_ancestor_prettierignore(self):
        (self.project / ".prettierignore").write_text('apps/nested/src/ignored.ts\n')
        nested = self.project / "apps/nested"
        self.install(nested, 1)
        (nested / "package.json").write_text('{}\n')
        (nested / ".prettierrc.json").write_text('{"semi":true}\n')
        self.check([self.case(nested, "src/ignored.ts", "typescript", 'const x="hi";\n', index=1, unchanged=True)])

    def test_no_project_formatter_skips_global_cwd_and_lsp(self):
        other = self.base / "other project"
        other.mkdir()
        cases = [self.case(other, "file." + ext, ft, text, unchanged=True) for ext, ft, text in (
            ("ts", "typescript", 'const x="hi";\n'), ("css", "css", '.a{color:red;}\n'),
            ("yaml", "yaml", 'items: [1,2]\n'))]
        self.check(cases, missing=True)
        self.assertFalse((self.home / "formatter-calls").exists())

    def test_shell_formatting_stays_disabled(self):
        cases = [self.case(self.project, ft + ".sh", ft, 'echo    hello\n', unchanged=True) for ft in ("sh", "bash")]
        self.check(cases)
        self.assertFalse((self.home / "formatter-calls").exists())

    def test_other_filetypes_skip_path_tools_and_lsp(self):
        cases = [self.case(self.project, "file." + ext, ft, text, unchanged=True) for ext, ft, text in (
            ("lua", "lua", 'local x={a=1}\n'), ("py", "python", 'x={"a":1}\n'),
            ("go", "go", 'package main\n'))]
        self.check(cases)
        self.assertFalse((self.home / "formatter-calls").exists())

    def test_never_borrows_dependencies_outside_repository(self):
        self.install(self.base, 1)
        separate = self.base / "separate repository"
        (separate / ".git").mkdir(parents=True)
        submodule = self.project / "apps/submodule"
        submodule.mkdir(parents=True)
        (submodule / ".git").write_text("gitdir: fixture\n")
        package = self.base / "package without git"
        package.mkdir()
        (package / "package.json").write_text('{}\n')
        cases = [self.case(root, "src/file.ts", "typescript", 'const x="hi";\n', unchanged=True)
                 for root in (separate, submodule, package)]
        self.check(cases, missing=True)
        self.assertFalse((self.home / "formatter-calls").exists())

    def test_formatter_failure_preserves_text(self):
        binary = self.project / "node_modules/.bin/prettier"
        binary.write_text('#!/bin/sh\necho "fixture formatter failed" >&2\nexit 2\n')
        self.check([self.case(self.project, "file.ts", "typescript", 'const x="hi";\n', unchanged=True)], failure=True)

    def test_timeout_preserves_text_without_fallback(self):
        binary = self.project / "node_modules/.bin/prettier"
        binary.write_text('#!/bin/sh\nsleep 1\nprintf "unexpected edit\\n"\n')
        self.check([self.case(self.project, "file.ts", "typescript", 'const x="hi";\n', unchanged=True)],
                   timeout_ms=20, timeout_error=True)

    def test_invalid_timeout_is_rejected(self):
        (self.config / "local.lua").write_text('return {features={format_on_save=true},format_timeout_ms=0}\n')
        lua = self.home / "invalid-timeout.lua"
        lua.write_text('''
vim.opt.rtp:prepend(vim.fn.stdpath("config"))
local warned = false
vim.notify = function(message) warned = message:find("format_timeout_ms", 1, true) ~= nil end
local settings = require("config.settings")
if not (warned and settings.format_timeout_ms == 3000 and not settings.features.format_on_save) then
  vim.cmd("cquit 1")
end
vim.cmd("qa!")
''')
        result = subprocess.run([str(NVIM), "--headless", "-u", "NONE", "-i", "NONE", "-l", str(lua)],
                                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class EslintTests(ProjectToolsTests):
    def install_eslint(self, root, index):
        binary = root / "node_modules/.bin/eslint"
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/bin/sh\nprintf "%s\\n" ' + shlex.quote(ESLINT_VERSIONS[index])
                          + ' >> "$ESLINT_TEST_LOG"\nexec ' + shlex.quote(str(ESLINT[index])) + ' "$@"\n')
        binary.chmod(0o755)
        parser = root / "node_modules/@typescript-eslint/parser"
        parser.parent.mkdir(parents=True, exist_ok=True)
        parser.symlink_to(PREFIXES[index + 2] / "node_modules/@typescript-eslint/parser")
        (root / "package.json").write_text('{}\n')
        if index == 0:
            (root / ".eslintrc.json").write_text(json.dumps({
                "root": True, "parser": "@typescript-eslint/parser",
                "parserOptions": {"ecmaVersion": 2022, "sourceType": "module", "ecmaFeatures": {"jsx": True}},
                "rules": {"no-console": "error"},
            }))
            (root / ".eslintignore").write_text('ignored.js\n')
        else:
            (root / "eslint.config.cjs").write_text('''
module.exports = [
  { ignores: ["ignored.js"] },
  { files: ["**/*.{js,jsx,ts,tsx}"], languageOptions: {
      parser: require("@typescript-eslint/parser"),
      parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } }
    }, rules: { "no-console": "warn" } }
];
''')
        return binary

    def lint_case(self, root, filename, filetype, text='console.log("hello");\n', rule="no-console", severity=1, **extra):
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return {"path": str(path), "filetype": filetype, "text": text,
                "rule": rule, "severity": severity, **extra}

    def check_lint(self, cases, enabled=True, legacy_lsp=False):
        if enabled:
            (self.config / "local.lua").write_text('return {features={eslint=true},servers={eslint=true}}\n')
        payload = self.home / "lint-cases.json"
        payload.write_text(json.dumps(cases))
        lua = self.home / "lint-check.lua"
        lua.write_text('''
vim.opt.rtp:prepend(vim.fn.stdpath("config"))
vim.opt.rtp:prepend(vim.env.LINT_FIXTURE)
local notices = {}
vim.notify_once = function(message) table.insert(notices, tostring(message)) end
local function check()
  local spec = require("plugins.linting")
  local enabled = vim.env.ESLINT_ENABLED == "1"
  assert(spec.enabled == enabled)
  if vim.env.ESLINT_LEGACY_LSP == "1" then
    package.preload.cmp_nvim_lsp = function() return {default_capabilities=function() return {} end} end
    package.preload["mason-registry"] = function() return {on=function() end} end
    vim.lsp.config("eslint", {cmd={"vscode-eslint-language-server", "--stdio"}, filetypes={"javascript"}})
    require("config.lsp").setup()
    assert(not vim.lsp.is_enabled("eslint"))
  end
  if enabled then spec.config() end
  local cases = vim.json.decode(table.concat(vim.fn.readfile(vim.env.ESLINT_CASES), "\\n"))
  for _, case in ipairs(cases) do
    vim.api.nvim_cmd({cmd="edit", args={case.path}}, {})
    vim.bo.filetype = case.filetype
    if enabled then
      local lint = require("lint")
      local ns = lint.get_namespace("eslint")
      assert(vim.wait(15000, function() return #lint.get_running(0) == 0 end), "ESLint did not finish")
      vim.wait(20, function() return false end)
      local diagnostics = vim.diagnostic.get(0, {namespace=ns})
      if case.rule ~= "" then
        assert(#diagnostics > 0, vim.inspect(notices))
        assert(diagnostics[1].code == case.rule and diagnostics[1].severity == case.severity, vim.inspect(diagnostics))
      elseif case.error then
        assert(#diagnostics > 0 and diagnostics[1].message:find(case.error, 1, true), vim.inspect(diagnostics))
      elseif case.ignored then
        for _, diagnostic in ipairs(diagnostics) do
          assert(diagnostic.message:lower():find("ignored", 1, true), vim.inspect(diagnostics))
        end
      else
        assert(#diagnostics == 0, vim.inspect(diagnostics))
      end
      assert(not vim.bo.modified, "ESLint must not edit buffers")
      if case.clear then
        vim.api.nvim_buf_set_lines(0, 0, -1, false, {"const answer = 42;"})
        vim.cmd("silent write")
        assert(vim.wait(15000, function() return #lint.get_running(0) == 0 end))
        vim.wait(20, function() return false end)
        assert(#vim.diagnostic.get(0, {namespace=ns}) == 0)
      end
    else
      assert(not package.loaded.lint)
      vim.cmd("silent write")
    end
    if not case.clear then
      local file = assert(io.open(case.path, "rb"))
      local content = file:read("*a"); file:close()
      assert(content == case.text)
    end
  end
  assert(#notices == 0, table.concat(notices, "\\n"))
end
local ok, err = pcall(check)
if not ok then io.stderr:write(tostring(err) .. "\\n"); vim.cmd("cquit 1") end
vim.cmd("qa!")
''')
        env = {**self.env, "ESLINT_CASES": str(payload), "ESLINT_ENABLED": "1" if enabled else "0",
               "ESLINT_LEGACY_LSP": "1" if legacy_lsp else "0"}
        result = subprocess.run([str(NVIM), "--headless", "-u", "NONE", "-i", "NONE", "-l", str(lua)],
                                cwd=self.project, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / "global-tools-called").exists())

    def test_default_off(self):
        self.install_eslint(self.project, 0)
        self.check_lint([self.lint_case(self.project, "file.js", "javascript")], enabled=False)
        self.assertFalse((self.home / "linter-calls").exists())

    def test_eslint8_open_save_and_clear(self):
        self.install_eslint(self.project, 0)
        self.check_lint([self.lint_case(self.project, "file.js", "javascript", clear=True)])
        self.assertEqual((self.home / "linter-calls").read_text().splitlines(), [ESLINT_VERSIONS[0]] * 2)

    def test_nearest_eslint9_flat_config_and_typescript(self):
        self.install_eslint(self.project, 0)
        nested = self.project / "apps/nested"
        self.install_eslint(nested, 1)
        cases = [self.lint_case(self.project, "apps/hoisted/file.js", "javascript")]
        for extension, ft, text in (
            ("ts", "typescript", 'const x: number = 1; console.log(x);\n'),
            ("tsx", "typescriptreact", 'const C = () => <div/>; console.log(C);\n'),
            ("jsx", "javascriptreact", 'const C = () => <div/>; console.log(C);\n')):
            cases.append(self.lint_case(nested, "src/file." + extension, ft, text, severity=2))
        self.check_lint(cases)
        self.assertEqual((self.home / "linter-calls").read_text().splitlines(),
                         [ESLINT_VERSIONS[0]] + [ESLINT_VERSIONS[1]] * 3)

    def test_missing_eslint_never_uses_global_cwd_or_parent(self):
        self.install_eslint(self.project, 0)
        self.install_eslint(self.base, 1)
        other = self.base / "separate repository"
        (other / ".git").mkdir(parents=True)
        self.check_lint([self.lint_case(other, "file.js", "javascript", rule="")])
        self.assertFalse((self.home / "linter-calls").exists())

    def test_ignores_are_handled_by_project_eslint(self):
        self.install_eslint(self.project, 0)
        self.check_lint([self.lint_case(self.project, "ignored.js", "javascript", rule="", ignored=True)])

    def test_configuration_failure_is_visible(self):
        self.install_eslint(self.project, 0)
        (self.project / ".eslintrc.json").write_text('{ broken config')
        self.check_lint([self.lint_case(self.project, "file.js", "javascript", rule="", error=".eslintrc.json")])

    def test_global_eslint_language_server_is_never_enabled(self):
        self.check_lint([self.lint_case(self.project, "file.js", "javascript", rule="")], legacy_lsp=True)
        self.assertFalse((self.home / "linter-calls").exists())

    def test_lazy_first_save_formats_and_lints(self):
        self.install_eslint(self.project, 1)
        (self.config / "local.lua").write_text('return {features={format_on_save=true,eslint=true},format_timeout_ms=10000}\n')
        path = self.project / "first.ts"
        path.write_text('console.log("hello");\n')
        lua = self.home / "lazy-check.lua"
        lua.write_text('''
vim.opt.rtp:prepend(vim.fn.stdpath("config"))
vim.opt.rtp:prepend(vim.env.LAZY_FIXTURE)
vim.o.loadplugins = true -- -u NONE disables plugin loading; exercise Lazy's normal startup.
vim.cmd("filetype on")
local function check()
  local formatter = require("plugins.formatting")[1]
  formatter.dir = vim.env.CONFORM_FIXTURE
  local linter = require("plugins.linting")
  linter.dir = vim.env.LINT_FIXTURE
  require("lazy").setup({formatter, linter}, {
    root=vim.fn.stdpath("data") .. "/lazy", local_spec=false,
    lockfile=vim.fn.stdpath("state") .. "/lazy-lock.json",
    install={missing=false}, checker={enabled=false},
    change_detection={enabled=false}, rocks={enabled=false},
    readme={enabled=false},
  })
  vim.api.nvim_cmd({cmd="edit", args={vim.env.LAZY_TEST_FILE}}, {})
  local plugins = require("lazy.core.config").plugins
  assert(vim.wait(15000, function() return #vim.diagnostic.get(0) > 0 end),
    "No initial ESLint diagnostics: " .. vim.inspect({filetype=vim.bo.filetype, plugin=plugins["nvim-lint"],
      executable=require("config.project_tools").executable(vim.api.nvim_buf_get_name(0), "eslint")}))
  assert(not plugins["conform.nvim"]._.loaded, "Formatter loaded before the first save")
  vim.cmd("silent write")
  assert(plugins["conform.nvim"]._.loaded)
  assert(vim.api.nvim_buf_get_lines(0,0,1,false)[1] == "console.log('hello')")
  local lint = require("lint")
  assert(vim.wait(15000, function() return #lint.get_running(0) == 0 end))
  vim.wait(20, function() return false end)
  assert(vim.diagnostic.get(0, {namespace=lint.get_namespace("eslint")})[1].code == "no-console")
end
local ok, err = pcall(check)
if not ok then io.stderr:write(tostring(err) .. "\\n"); vim.cmd("cquit 1") end
vim.cmd("qa!")
''')
        result = subprocess.run([str(NVIM), "--headless", "-u", "NONE", "-i", "NONE", "-l", str(lua)],
                                cwd=self.project, env={**self.env, "LAZY_FIXTURE": str(LAZY), "LAZY_TEST_FILE": str(path)},
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / "global-tools-called").exists())


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *sys.argv[9:]], verbosity=2)
