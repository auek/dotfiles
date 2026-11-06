#!/usr/bin/env python3
"""Daily Stow/shell/tmux/theme workflows using tracked configs and real Oh My Zsh."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from test_support import stop_tmux

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(os.environ["DOTFILES_TEST_FIXTURES"])
TMUX = shutil.which("tmux")


class MakeStowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-restow-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo, self.home = base / "repo", base / "home"
        shutil.copytree(ROOT / "packages", self.repo / "packages")
        shutil.copy2(ROOT / "Makefile", self.repo / "Makefile")
        self.home.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("XDG_", "MAKE", "MFLAGS", "STOW_"))}
        self.env.update(HOME=str(self.home), PATH="/usr/bin:/bin")
        self.current = self.home / ".local/state/dotfiles/theme/current"
        self.current.parent.mkdir(parents=True)
        self.selection = self.repo / "packages/themes/.local/share/dotfiles/themes/gruvbox"
        self.current.symlink_to(self.selection, target_is_directory=True)
        # Existing selections must not be reinitialized. Poison the copied
        # command so even a regression cannot contact host reload services.
        (self.repo / "packages/themes/.local/bin/theme-set").write_text("#!/bin/sh\nexit 99\n")

    def make(self, target, success=True):
        result = subprocess.run(["make", target], cwd=self.repo, env=self.env,
                                capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_repeat_restow_refreshes_links_and_preserves_local_state(self):
        local_files = {
            ".config/nvim/local.lua": "return {servers={cssls=false}}\n",
            ".config/mise/config.local.toml": '[tools]\nnode = "lts"\n',
            ".config/hypr/hyprland.lua": '-- local desktop preferences\n',
            ".config/tmx/init.zsh": "# local session hook\n",
            ".zshrc.private": "# local shell preferences\n",
        }
        for name, contents in local_files.items():
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        foot = self.home / ".config/foot/foot.ini"
        foot.parent.mkdir()
        foot_source = self.repo / "packages/foot/.config/foot/foot.ini"
        foot.symlink_to(foot_source)
        source = self.repo / "packages/nvim/.config/nvim/lua/config"
        old, removed = source / "old.lua", source / "removed.lua"
        old.write_text("-- renamed after pull\n")
        removed.write_text("-- deleted after pull\n")
        self.make("stow")
        old.rename(source / "new.lua")
        removed.unlink()
        (source / "added.lua").write_text("-- added after pull\n")
        for _ in range(2):
            self.make("restow")
            config = self.home / ".config/nvim/lua/config"
            for name in ("old.lua", "removed.lua"):
                self.assertFalse(os.path.lexists(config / name), name)
            for name in ("new.lua", "added.lua"):
                self.assertTrue((config / name).is_symlink())
                self.assertEqual((config / name).resolve(), source / name)
            for name, contents in local_files.items():
                self.assertFalse((self.home / name).is_symlink(), name)
                self.assertEqual((self.home / name).read_text(), contents)
            self.assertEqual(self.current.readlink(), self.selection)
            self.assertEqual(foot.readlink(), foot_source)
            for name in ("waybar", "wofi", "mako"):
                self.assertFalse((self.home / ".config" / name).exists(), name)
            self.assertFalse((self.home / ".config/hypr/dotfiles.lua").exists())
        # A newly tracked path must not overwrite a machine-local file.
        conflict = self.home / ".config/nvim/lua/config/conflict.lua"
        conflict.write_text("-- preserve local file\n")
        (source / "conflict.lua").write_text("-- shared file\n")
        self.make("restow", success=False)
        self.assertFalse(conflict.is_symlink())
        self.assertEqual(conflict.read_text(), "-- preserve local file\n")
        self.assertEqual((source / "conflict.lua").read_text(), "-- shared file\n")

    def test_optional_includes_default_and_xdg_local_preferences(self):
        optional = {
            "opencode": ".config/opencode/opencode.jsonc",
            "claude": ".claude/settings.json",
            "espanso": ".config/espanso/config/default.yml",
        }
        for target in ("stow", "restow"):
            self.make(target)
            for name in optional.values():
                self.assertFalse(os.path.lexists(self.home / name), name)
        config = self.home / ".config/dotfiles/local.mk"
        config.parent.mkdir()
        contents = "STOW_INCLUDE = opencode claude espanso\n"
        config.write_text(contents)
        for target in ("stow", "restow"):
            self.make(target)
            for package, name in optional.items():
                self.assertTrue((self.home / name).is_symlink(), name)
                self.assertEqual((self.home / name).resolve(), self.repo / "packages" / package / name)
        # The local preference stays ordinary and follows XDG_CONFIG_HOME.
        xdg = self.home / "custom-config"
        self.env["XDG_CONFIG_HOME"] = str(xdg)
        moved = xdg / "dotfiles/local.mk"
        moved.parent.mkdir(parents=True)
        config.rename(moved)
        self.make("unstow")
        for name in optional.values():
            self.assertFalse(os.path.lexists(self.home / name), name)
        self.make("restow")
        moved.write_text("STOW_INCLUDE =\n")
        self.make("restow")
        for name in optional.values():
            self.assertTrue((self.home / name).is_symlink(), "Dropping an include removed " + name)
        moved.write_text(contents)
        self.make("unstow")
        self.assertFalse(moved.is_symlink())
        self.assertEqual(moved.read_text(), contents)
        self.assertFalse(os.path.lexists(self.home / ".config/nvim/init.lua"))
        for name in optional.values():
            self.assertFalse(os.path.lexists(self.home / name), name)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles runtime ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("MISE_", "__MISE_", "TMUX", "XDG_", "ZSH", "ZDOT", "SSH_"))}
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".data"), XDG_STATE_HOME=str(self.home / ".state"),
                        XDG_CACHE_HOME=str(self.home / ".cache"), TERM="xterm-256color",
                        PATH=f"{self.bin}:{FIXTURES / 'bin'}:/usr/bin:/bin")
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_VTNR", "ENV", "BASH_ENV"):
            self.env.pop(key, None)
        for package, filename in (("zshrc", ".zshrc"), ("zprofile", ".zprofile"), ("tmux", ".tmux.conf")):
            shutil.copy2(ROOT / "packages" / package / filename, self.home / filename)
        (self.home / ".oh-my-zsh").symlink_to(FIXTURES / "ohmyzsh", target_is_directory=True)
        (self.home / ".ssh").mkdir()
        (self.home / ".zshenv").write_text("zstyle ':omz:update' mode disabled\n"
                                           "zstyle :omz:plugins:ssh-agent quiet yes\n")
        (self.home / ".zshrc.private").write_text("export DOTFILES_LOCAL=loaded\n")
        # Agent/device/desktop access is an external boundary; no host services.
        self.mock("ssh-agent", '''printf "SSH_AUTH_SOCK='%s/mock-agent'; export SSH_AUTH_SOCK;\\n" "$HOME"''')
        self.mock("ssh-add", "exit 0")
        self.mock("ddcutil", 'echo unexpected-monitor-access >> "$HOME/unexpected"; exit 1')
        themes = self.home / ".local/share/dotfiles/themes"
        shutil.copytree(ROOT / "packages/themes/.local/share/dotfiles/themes", themes)
        self.current = self.home / ".local/state/dotfiles/theme/current"
        self.current.parent.mkdir(parents=True)
        self.current.symlink_to(themes / "everforest", target_is_directory=True)
        self.socket = self.home / "tmux.sock"
        self.addCleanup(self.stop_server)

    def stop_server(self):
        stop_tmux(TMUX, self.socket, self.env)

    def mock(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_checked(self, *args):
        result = subprocess.run(args, cwd=self.home, env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.stdout.strip()

    def tmux(self, *args):
        return self.run_checked(TMUX, "-S", str(self.socket), "-f", str(self.home / ".tmux.conf"), *args)

    def test_shell_startup_completion_and_local_override(self):
        for flags in ("-lc", "-ic", "-lic"):
            with self.subTest(flags=flags):
                code = 'node --version && nvim --version >/dev/null || exit; '
                if "i" in flags:
                    code += ('[[ "$DOTFILES_LOCAL" == loaded ]] || exit 1; '
                             '(( $+functions[compdef] && $+functions[_zsh_autosuggest_start] )) || exit 2; '
                             'tmx --help || exit; ')
                code += 'print startup-ok'
                self.assertIn("startup-ok", self.run_checked("zsh", flags, code))
        self.assertFalse((self.home / "unexpected").exists())

    def test_actual_tmux_config_and_directory_bindings(self):
        # The private hook signals after the real interactive shell has started.
        with (self.home / ".zshrc.private").open("a") as stream:
            stream.write('[[ -n "$TMUX" ]] && tmux wait-for -S shell-ready\n')
        project = self.home / "project with spaces"
        project.mkdir()
        self.tmux("new-session", "-d", "-s", "runtime", "-c", str(project), "-x", "120", "-y", "40")
        self.tmux("wait-for", "shell-ready")
        self.assertEqual(self.tmux("display-message", "-p", "#{window_index}"), "1")
        # Explicit sourcing surfaces errors that initial detached startup can hide.
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        for key in ('"', "%", "c"):
            with self.subTest(key=key):
                binding = shlex.split(self.tmux("list-keys", "-T", "prefix", key))
                command = binding[binding.index(key) + 1:]
                self.tmux(*command)
                self.tmux("wait-for", "shell-ready")
                self.assertEqual(self.tmux("display-message", "-p", "#{pane_current_path}"), str(project))
        self.assertEqual(self.tmux("display-message", "-p", "#{session_windows}"), "2")
        for index in range(3, 11):
            self.tmux("new-window", "-d", "-t", f":{index}", "sleep 60")
        for index in range(1, 11):
            key = f"M-{index % 10}"
            with self.subTest(key=key):
                binding = shlex.split(self.tmux("list-keys", "-T", "root", key))
                self.tmux(*binding[binding.index(key) + 1:])
                self.assertEqual(self.tmux("display-message", "-p", "#{window_index}"), str(index))

    def test_theme_switch_rejection_and_reload_failure(self):
        # Make every reload observable and harmless, including process signals.
        for name in ("tmux", "pgrep", "pkill", "makoctl", "hyprctl", "systemctl", "foot-reload"):
            self.mock(name, 'echo "$0 $*" >> "$HOME/reloads"; exit 1')
        command = ROOT / "packages/themes/.local/bin/theme-set"
        result = subprocess.run(["bash", str(command), "gruvbox"], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.current.resolve().name, "gruvbox")
        self.assertIn("warning:", result.stderr)
        self.assertEqual(self.run_checked("bash", str(command)), "gruvbox")
        (self.home / ".local/share/dotfiles/themes/everforest/tmux.conf").unlink()
        before = (self.home / "reloads").read_bytes()
        for theme in ("everforest", "missing", "../gruvbox"):
            result = subprocess.run(["bash", str(command), theme], env=self.env,
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.current.resolve().name, "gruvbox")
        self.assertEqual((self.home / "reloads").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
