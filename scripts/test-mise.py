#!/usr/bin/env python3
"""Exercise real mise/Zsh/Stow in disposable homes with pre-downloaded builds.

Usage: test-mise.py /path/to/mise /path/to/node-24.19.0 /path/to/other-node /path/to/neovim-tool
Node arguments contain bin/node. The last argument is a disposable mise fixture's
installs/aqua-neovim-neovim directory, including its generated backend metadata.
Requires Python 3.11+, Zsh, and GNU Stow. No tools are downloaded and no real
user configuration is loaded or changed.
"""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 5:
    sys.exit(__doc__)
MISE, NODE, OTHER_NODE, NVIM = [Path(arg).resolve() for arg in sys.argv[1:]]
STOW = shutil.which("stow")
if not STOW:
    sys.exit("GNU Stow must be on PATH")
OTHER_VERSION = subprocess.check_output(
    [str(OTHER_NODE / "bin/node"), "--version"], text=True).strip().removeprefix("v")
if OTHER_VERSION == "24.19.0":
    sys.exit("The other Node fixture must differ from 24.19.0 to test switching")
NVIM_BINARY = next(NVIM.glob("[0-9]*/*/bin/nvim"))
NVIM_VERSION = subprocess.check_output(
    [str(NVIM_BINARY), "--version"], text=True,
    env={**os.environ, "NVIM_LOG_FILE": os.devnull}).splitlines()[0].split("v", 1)[1]


class MiseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mise check ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.checkout = self.base / "checkout with spaces"
        self.packages = self.checkout / "packages"
        for package in ("mise", "tealdeer", "zprofile", "zshrc"):
            shutil.copytree(ROOT / "packages" / package, self.packages / package)
        self.config = self.packages / "mise/.config/mise/config.toml"
        self.manifest = tomllib.loads(self.config.read_text())
        # Register only the supplied builds; avoid resolving unrelated tools.
        self.config.write_text('[tools]\n[settings]\nidiomatic_version_file_enable_tools = ["node"]\n')
        bindir = self.home / ".local/bin"
        bindir.mkdir(parents=True)
        (bindir / "mise").symlink_to(MISE)
        (self.home / ".oh-my-zsh").mkdir()
        (self.home / ".oh-my-zsh/oh-my-zsh.sh").touch()
        # An activated parent exports a PATH diff that can restore its host
        # tool directories even after we replace HOME and PATH for the fixture.
        parent_env = {key: value for key, value in os.environ.items()
                      if not key.startswith(("MISE_", "__MISE_"))}
        self.env = {**parent_env, "HOME": str(self.home),
                    "PATH": f"{bindir}:{bindir}:/usr/bin:/bin",
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_DATA_HOME": str(self.home / ".local/share"),
                    "XDG_STATE_HOME": str(self.home / ".local/state"),
                    "XDG_CACHE_HOME": str(self.home / ".cache"),
                    "MISE_CONFIG_DIR": str(self.home / ".config/mise"),
                    "MISE_DATA_DIR": str(self.home / ".local/share/mise"),
                    "MISE_STATE_DIR": str(self.home / ".local/state/mise"),
                    "MISE_CACHE_DIR": str(self.home / ".cache/mise"),
                    "MISE_HIDE_UPDATE_WARNING": "1", "SSH_AUTH_SOCK": "fixture",
                    "NVIM_LOG_FILE": str(self.home / "nvim.log")}
        for key in ("ZDOTDIR", "MISE_GLOBAL_CONFIG_FILE", "MISE_NODE_VERSION", "MISE_ENV",
                    "SSH_CONNECTION", "DISPLAY", "WAYLAND_DISPLAY", "XDG_VTNR"):
            self.env.pop(key, None)
        self.stow("mise", "tealdeer", "zprofile", "zshrc")
        # Preserve real Aqua installation metadata, which `mise link` alone
        # does not generate for explicit backends. Copy it before each check.
        shutil.copytree(NVIM, self.home / ".local/share/mise/installs/aqua-neovim-neovim",
                        symlinks=True)
        for tool, directory in (("node@24.19.0", NODE),
                                (f"node@{OTHER_VERSION}", OTHER_NODE)):
            self.run_checked([str(MISE), "link", tool, str(directory)])
        self.config.write_text(
            '[tools]\nnode = "24.19.0"\n"aqua:neovim/neovim" = "latest"\n'
            '[settings]\nidiomatic_version_file_enable_tools = ["node"]\n')
        self.run_checked([str(MISE), "reshim"])
        # An old Bob launcher must lose to mise, even before the first prompt.
        legacy = self.home / "legacy-nvim"
        legacy.write_text("#!/bin/sh\necho 'old Bob launcher selected' >&2\nexit 91\n")
        legacy.chmod(0o755)
        (bindir / "nvim").symlink_to(legacy)

    def run_checked(self, args, cwd=None):
        result = subprocess.run(args, cwd=cwd or self.home, env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def stow(self, *args):
        return self.run_checked([STOW, "--no-folding", f"--dir={self.packages}",
                                 f"--target={self.home}", *args])

    def shell(self, flags, command, cwd=None):
        return self.run_checked(["zsh", flags, command], cwd)

    def test_manifest_and_system_trust(self):
        tools = self.manifest["tools"]
        self.assertEqual(tools.pop("node"), "24.19.0")
        self.assertTrue(tools)
        self.assertTrue(all(version == "latest" for version in tools.values()))
        self.assertEqual(self.manifest["settings"]["idiomatic_version_file_enable_tools"], ["node"])
        config = tomllib.loads((self.home / ".config/tealdeer/config.toml").read_text())
        self.assertEqual(config["updates"]["tls_backend"], "rustls-with-native-roots")

    def test_first_command_in_login_and_interactive_shells(self):
        for flags in ("-lc", "-lic", "-ic"):
            with self.subTest(flags=flags):
                output = self.shell(flags, 'node --version; npm --version; npx --version; '
                                    'command -v node; command -v nvim; nvim --version')
                self.assertIn("v24.19.0", output)
                self.assertEqual(output.splitlines().count("11.17.0"), 2)
                self.assertIn(str(self.home / ".local/share/mise"), output)
                self.assertIn(f"NVIM v{NVIM_VERSION}", output)

    def test_project_node_files_and_return_to_global(self):
        for filename in (".nvmrc", ".node-version"):
            project = self.home / filename.removeprefix(".")
            project.mkdir()
            (project / filename).write_text(OTHER_VERSION + "\n")
            for flags in ("-lc", "-ic"):
                with self.subTest(filename=filename, flags=flags):
                    output = self.shell(flags, 'node --version; cd "$HOME"; node --version', project)
                    self.assertEqual(output.splitlines(), [f"v{OTHER_VERSION}", "v24.19.0"])

    def test_machine_local_node_override_and_project_precedence(self):
        before = self.config.read_bytes()
        local = self.home / ".config/mise/config.local.toml"
        contents = f'[tools]\nnode = "{OTHER_VERSION}"\n'
        local.write_text(contents)
        self.stow("--restow", "mise")
        self.assertEqual(local.read_text(), contents)
        for flags in ("-lc", "-lic", "-ic"):
            with self.subTest(flags=flags):
                self.assertEqual(self.shell(flags, "node --version"), f"v{OTHER_VERSION}")
        for filename in (".nvmrc", ".node-version"):
            project = self.home / ("local-override-" + filename.removeprefix("."))
            project.mkdir()
            (project / filename).write_text("24.19.0\n")
            for flags in ("-lc", "-ic"):
                with self.subTest(filename=filename, flags=flags):
                    output = self.shell(flags, 'node --version; cd "$HOME"; node --version', project)
                    self.assertEqual(output.splitlines(), ["v24.19.0", f"v{OTHER_VERSION}"])
        self.assertEqual(self.config.read_bytes(), before)
        self.stow("--delete", "mise")
        self.assertEqual(local.read_text(), contents)

    def test_inherited_subprocess_path_and_neovim_node(self):
        self.assertEqual(self.shell("-lic", "zsh -c 'node --version'"), "v24.19.0")
        lua = self.home / "node-check.lua"
        lua.write_text('local r = vim.system({"node", "--version"}, {text=true}):wait()\n'
                       'if r.code ~= 0 or vim.trim(r.stdout) ~= "v24.19.0" then\n'
                       '  io.stderr:write(vim.inspect(r)); vim.cmd("cquit 1")\n'
                       'end\nprint("Neovim child Node OK")\nvim.cmd("qa")\n')
        self.shell("-lic", "nvim --headless -u NONE -i NONE -l " + shlex.quote(str(lua)))

    def test_repeatable_profile_and_unique_path(self):
        output = self.shell("-lc", 'source ~/.zprofile; source ~/.zprofile; '
                            'print -l -- $path | sort | uniq -d')
        self.assertEqual(output, "")
        before = self.config.read_bytes()
        self.run_checked([str(MISE), "reshim"])
        self.assertEqual(self.config.read_bytes(), before)

    def test_fixture_path_isolation(self):
        for flags in ("-lc", "-lic", "-ic"):
            with self.subTest(flags=flags):
                paths = self.shell(flags, "print -l -- $path").splitlines()
                for path in paths:
                    # Login shells may add distro paths through /etc/profile.
                    self.assertTrue(path in ("/bin", "/sbin") or path.startswith("/usr/") or
                                    path.startswith(str(self.home) + "/"), path)

    def test_stow_conflict_and_safe_removal(self):
        unrelated = self.home / ".config/tealdeer/local-note"
        unrelated.write_text("keep me\n")
        self.stow("--delete", "mise", "tealdeer")
        self.assertEqual(unrelated.read_text(), "keep me\n")
        target = self.home / ".config/mise/config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# existing local settings\n")
        result = subprocess.run([STOW, "--simulate", "--no-folding", f"--dir={self.packages}",
                                 f"--target={self.home}", "mise"],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "# existing local settings\n")

    def test_bootstrap_installs_declared_tools_without_rewriting_config(self):
        log = self.home / "bootstrap-log"
        for name in ("mise", "uv", "llm"):
            mock = self.home / ".local/bin" / name
            mock.unlink(missing_ok=True)
            mock.write_text('#!/bin/sh\nprintf "%s %s\\n" "$PWD" "$*" >> "$HOME/bootstrap-log"\n')
            mock.chmod(0o755)
        phase = (ROOT / "setup.sh").read_text().split("step \"11/12", 1)[1]
        phase = 'step "11/12' + phase.split("# ─── Step 12:", 1)[0]
        prelude = ('set -eu; step() { :; }; info() { :; }; success() { :; }; '
                   'warning() { :; }; PROFILE="$1";\n')
        before = self.config.read_bytes()
        for _ in range(2):
            self.run_checked(["bash", "-c", prelude + phase, "check", "full"])
        self.assertEqual(log.read_text().splitlines(),
                         [f"{self.home} install", f"{self.home} reshim"] * 2)
        self.assertEqual(self.config.read_bytes(), before)
        log.unlink()
        for profile in ("slim", "server"):
            self.run_checked(["bash", "-c", prelude + phase, "check", profile])
        self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
