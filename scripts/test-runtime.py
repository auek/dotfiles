#!/usr/bin/env python3
"""Daily shell/tmux/theme workflows using tracked configs and real Oh My Zsh."""

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
