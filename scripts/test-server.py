#!/usr/bin/env python3
"""Server Bash, Stow and tmux workflows in disposable homes, without setup.sh."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from test_support import stop_tmux


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
TMUX = shutil.which("tmux")


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-server-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("TMUX", "XDG_", "MAKE", "MFLAGS", "STOW_", "BASH_FUNC_"))}
        for key in ("BASH_ENV", "ENV", "CDPATH", "PROMPT_COMMAND"):
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), PATH="/usr/bin:/bin", SHELL=BASH,
                        TERM="xterm-256color", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        self.socket = self.home / "tmux.sock"
        self.addCleanup(stop_tmux, TMUX, self.socket, self.env)
        self.make("stow-server")

    def checked(self, *args):
        result = subprocess.run(args, cwd=self.home, env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def make(self, target):
        return self.checked("make", "--no-print-directory", "-C", str(ROOT), target)

    def bash(self, code, interactive=False):
        if interactive:
            return self.checked(BASH, "--noprofile", "--rcfile", str(self.home / ".bashrc"), "-ic", code)
        return self.checked(BASH, "--noprofile", "--norc", "-c", 'source "$HOME/.bashrc"; ' + code)

    def tmux(self, *args):
        return self.checked(TMUX, "-S", str(self.socket), "-f", str(self.home / ".tmux.conf"), *args)

    def test_bash_startup_and_private_overrides(self):
        code = 'tmx --help >/dev/null && printf "%s|%s" "$HISTFILE" "$HISTSIZE"'
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                self.assertEqual(self.bash(code, interactive), f"{self.home}/.bash_history|500000")
        private = self.home / ".bashrc.private"
        private.write_text('export DOTFILES_SERVER_LOCAL=loaded\nalias p="printf private-override"\n')
        self.assertEqual(self.bash('printf "%s|" "$DOTFILES_SERVER_LOCAL"; eval p', True),
                         "loaded|private-override")
        self.assertFalse(private.is_symlink())

    def test_git_status_and_navigation_without_writing_shortcuts(self):
        self.checked("git", "init", "-b", "main")
        (self.home / "pending.txt").write_text("pending\n")
        self.assertEqual(self.bash('gst -- pending.txt', True), "?? pending.txt")
        self.assertEqual(self.bash('alias gco'), "alias gco='git checkout'")
        self.bash('for name in gp gpsup gcane gcam gcmsg gcb; do '
                  'if alias "$name" >/dev/null 2>&1; then exit 1; fi; done')

    def test_restow_and_unstow_preserve_private_files(self):
        local_files = {
            ".bashrc.private": "export DOTFILES_SERVER_LOCAL=preserved\n",
            ".config/tmx/init.bash": "# local session layout\n",
        }
        for name, contents in local_files.items():
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        for target in ("stow-server", "stow-server", "unstow-server"):
            self.make(target)
            for name, contents in local_files.items():
                path = self.home / name
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.read_text(), contents)
        for name in (".bashrc", ".tmux.conf", ".vimrc"):
            self.assertFalse(os.path.lexists(self.home / name))
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertFalse((self.home / ".config/mise").exists())

    def test_actual_tmux_config_and_directory_bindings(self):
        private = self.home / ".bashrc.private"
        private.write_text('[[ -n "$TMUX" ]] && tmux wait-for -S server-shell-ready\n')
        project = self.home / "project with spaces"
        project.mkdir()
        # Avoid host login profiles while exercising the real interactive Bash rc.
        shell_command = f'exec {shlex.quote(BASH)} --noprofile --rcfile "$HOME/.bashrc" -i'
        self.tmux("new-session", "-d", "-s", "server", "-c", str(project),
                  "-x", "120", "-y", "40", shell_command)
        self.tmux("wait-for", "server-shell-ready")
        self.tmux("source-file", str(self.home / ".tmux.conf"))
        self.tmux("set-option", "-g", "default-command", shell_command)
        for key in ('"', "%", "c"):
            with self.subTest(key=key):
                binding = shlex.split(self.tmux("list-keys", "-T", "prefix", key))
                self.tmux(*binding[binding.index(key) + 1:])
                self.tmux("wait-for", "server-shell-ready")
                self.assertEqual(self.tmux("display-message", "-p", "#{pane_current_path}"), str(project))
        self.assertEqual(self.tmux("display-message", "-p", "#{session_windows}"), "2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
