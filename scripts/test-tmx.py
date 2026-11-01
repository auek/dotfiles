#!/usr/bin/env python3
"""Exercise the shared tmx function using disposable homes and tmux sockets."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_support import stop_tmux


ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")
TMUX = shutil.which("tmux")
if not ZSH or not TMUX:
    sys.exit("requires Zsh and tmux")


class TmxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tmx-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.project = self.home / "project with spaces; literal"
        self.project.mkdir()
        self.socket = self.home / "tmux.sock"
        self.log = self.home / "commands.jsonl"
        self.config = self.home / "tmux.conf"
        # Nonzero indexes catch accidental assumptions about window 0/pane 0.
        self.config.write_text("set -g default-shell /bin/sh\n"
                               # No terminal is attached in these tests. Older
                               # tmux otherwise recalculates to 80x24 between
                               # commands, discarding new-session's -x/-y size.
                               "set -g window-size manual\n"
                               "set -g base-index 3\n"
                               "set -g pane-base-index 4\n"
                               "set -g status off\n")
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("MISE_", "__MISE_", "TMUX", "ZSH", "ZDOT"))}
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".local/share"),
                        XDG_STATE_HOME=str(self.home / ".local/state"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        PATH=f"{self.bin}:/usr/bin:/bin", TERM="xterm-256color",
                        TMX_TEST_SOCKET=str(self.socket), TMX_TEST_CONFIG=str(self.config),
                        TMX_TEST_LOG=str(self.log), TMX_TEST_REAL=TMUX, SSH_AUTH_SOCK="fixture")
        self.env.pop("ZDOTDIR", None)
        self.addCleanup(self.stop_server)
        # Only attachment/client switching are mocked. All other operations use
        # a real server on our private socket, never the user's running server.
        (self.bin / "tmux").write_text(f"#!{sys.executable}\n" + '''
import json
import os
import sys
args = sys.argv[1:]
with open(os.environ["TMX_TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[0] in ("attach-session", "switch-client"):
    sys.exit(int(os.environ.get("TMX_TEST_ATTACH_RESULT", "0")))
if args[0] == "new-session" and os.environ.get("TMX_TEST_FAIL_CREATE"):
    print("simulated creation failure", file=sys.stderr)
    sys.exit(1)
if args[0] == "list-sessions" and os.environ.get("TMX_TEST_FAIL_LIST"):
    print("simulated permission denied", file=sys.stderr)
    sys.exit(1)
real = os.environ["TMX_TEST_REAL"]
os.execv(real, [real, "-S", os.environ["TMX_TEST_SOCKET"],
               "-f", os.environ["TMX_TEST_CONFIG"], *args])
''')
        (self.bin / "tmux").chmod(0o755)
        (self.home / ".oh-my-zsh").mkdir()
        (self.home / ".oh-my-zsh/oh-my-zsh.sh").touch()
        self.function = ROOT / "packages/zshrc/.zshrc"

    def stop_server(self):
        stop_tmux(TMUX, self.socket, self.env)

    def run_tmx(self, *args, code='tmx "$@"', **env):
        return subprocess.run([ZSH, "-f", "-c", 'source "$1"; shift; ' + code,
                               "tmx-check", str(self.function), *args],
                              cwd=self.project, env={**self.env, **env},
                              text=True, capture_output=True, timeout=10)

    def real_tmux(self, *args):
        result = subprocess.run([TMUX, "-S", str(self.socket), "-f", str(self.config), *args],
                                env=self.env, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def hook(self, body, config_home=None):
        hook = (config_home or self.home / ".config") / "tmx/init.zsh"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(body)
        return hook

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_loading_defines_only_tmx_without_running_commands_or_hook(self):
        self.hook('print ran > "$HOME/hook-ran"\n')
        self.assert_ok(self.run_tmx(code='(( ${+functions[tmx]} && ! ${+functions[dev]} ))'))
        self.assertEqual(self.commands(), [])
        self.assertFalse((self.home / "hook-ran").exists())

    def test_help_validation_and_missing_tmux(self):
        for flag in ("-h", "--help"):
            result = self.run_tmx(flag, PATH="/nonexistent")
            self.assert_ok(result)
            self.assertIn("Usage: tmx", result.stdout)
        for args in (("-x",), ("",), ("bad:name",), ("bad.name",), ("$1",), ("a", "b", "c")):
            with self.subTest(args=args):
                self.assertNotEqual(self.run_tmx(*args).returncode, 0)
        result = self.run_tmx("example", PATH="/nonexistent")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tmux is not installed", result.stderr)
        self.assertEqual(self.commands(), [])

    def test_listing_without_creation_or_hook(self):
        self.hook('print ran > "$HOME/hook-ran"\n')
        result = self.run_tmx()
        self.assert_ok(result)
        self.assertIn("No tmux sessions", result.stdout)
        self.real_tmux("new-session", "-d", "-s", "existing")
        result = self.run_tmx()
        self.assert_ok(result)
        self.assertIn("existing:", result.stdout)
        self.assertFalse((self.home / "hook-ran").exists())
        self.assertEqual([cmd[0] for cmd in self.commands()], ["list-sessions"] * 2)
        result = self.run_tmx(TMX_TEST_FAIL_LIST="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("permission denied", result.stderr)

    def test_plain_session_defaults_to_current_directory(self):
        # A project-local file must never be treated as the machine-local hook.
        (self.project / "init.zsh").write_text('print unsafe > "$HOME/unsafe"\n')
        result = self.run_tmx("plain", COLUMNS="200", LINES="60")
        self.assert_ok(result)
        panes = self.real_tmux("list-panes", "-t", "=plain", "-F",
                               "#{pane_current_path}|#{window_width}|#{window_height}")
        self.assertEqual(panes, f"{self.project}|200|60")
        self.assertEqual(self.real_tmux("display-message", "-p", "-t", "=plain:",
                                       "#{session_windows}"), "1")
        self.assertFalse((self.home / "unsafe").exists())
        self.assertEqual(self.commands()[-1][0], "attach-session")

    def test_relative_directory_and_literal_session_name(self):
        nested = self.project / "nested path"
        nested.mkdir()
        self.assert_ok(self.run_tmx("name with spaces; echo unsafe", "nested path"))
        self.assertEqual(self.real_tmux("list-panes", "-t", "=name with spaces; echo unsafe",
                                       "-F", "#{pane_current_path}"), str(nested))

    def test_existing_session_ignores_location_and_does_not_rerun_hook(self):
        self.hook('print ran >> "$HOME/hook-ran"\n')
        self.assert_ok(self.run_tmx("project", str(self.project)))
        self.assert_ok(self.run_tmx("project", "/missing/location"))
        self.assertEqual((self.home / "hook-ran").read_text(), "ran\n")
        self.assertEqual(sum(cmd[0] == "new-session" for cmd in self.commands()), 1)
        self.assertEqual(self.commands()[-1], ["attach-session", "-t", "=project"])

    def test_relative_xdg_directory_cannot_load_project_hook(self):
        self.hook('print local > "$HOME/hook-ran"\n')
        self.hook('print unsafe > "$HOME/unsafe"\n', self.project / "relative-config")
        self.assert_ok(self.run_tmx("relative-xdg", XDG_CONFIG_HOME="relative-config"))
        self.assertEqual((self.home / "hook-ran").read_text(), "local\n")
        self.assertFalse((self.home / "unsafe").exists())

    def test_exact_session_match_not_prefix_or_pattern(self):
        self.assert_ok(self.run_tmx("project-long"))
        self.assert_ok(self.run_tmx("project"))
        self.assert_ok(self.run_tmx("project*"))
        self.assertEqual(set(self.real_tmux("list-sessions", "-F", "#{session_name}").splitlines()),
                         {"project-long", "project", "project*"})

    def test_hook_ids_split_ratios_and_program_startup(self):
        self.hook('''
session=$1 window=$2 pane=$3 directory=$4
print -r -- "$session|$window|$pane|$directory" > "$HOME/hook-args"
tmux split-window -d -h -p "$TMX_TEST_PERCENT" -t "$pane" -c "$directory"
tmux send-keys -t "$pane" -l 'printf ready > "$HOME/program-ran"'
tmux send-keys -t "$pane" Enter
# Wait deterministically for the pane command, without polling or sleeping.
tmux send-keys -t "$pane" -l 'tmux wait-for -S tmx-program-ready'
tmux send-keys -t "$pane" Enter
tmux wait-for tmx-program-ready
''')
        for percent in (20, 50):
            with self.subTest(percent=percent):
                name = f"split-{percent}"
                self.assert_ok(self.run_tmx(name, COLUMNS="200", LINES="60", XDG_CONFIG_HOME="",
                                            TMX_TEST_PERCENT=str(percent)))
                session, window, pane, directory = (self.home / "hook-args").read_text().strip().split("|")
                self.assertTrue(session.startswith("$"))
                self.assertTrue(window.startswith("@"))
                self.assertTrue(pane.startswith("%"))
                self.assertEqual(directory, str(self.project))
                panes = self.real_tmux("list-panes", "-t", window, "-F",
                                       "#{pane_id}|#{pane_width}|#{pane_current_path}|#{pane_active}")
                rows = [row.split("|") for row in panes.splitlines()]
                self.assertEqual(len(rows), 2)
                self.assertEqual([row[2] for row in rows], [str(self.project)] * 2)
                self.assertEqual(rows[0][0], pane)
                self.assertEqual(rows[0][3], "1")
                self.assertLessEqual(abs(int(rows[1][1]) - 200 * percent / 100), 1)
                self.assertEqual((self.home / "program-ran").read_text(), "ready")

    def test_xdg_hook_isolation_and_failure_preserves_session(self):
        xdg = self.home / "custom config"
        self.hook('print wrong > "$HOME/wrong-hook"\n')
        self.hook('cd /\nexport TMX_LEAK=bad\nfalse\nprint unreachable\n', xdg)
        result = self.run_tmx("failed-hook", XDG_CONFIG_HOME=str(xdg),
                              code='tmx "$@"; result=$?; '
                                   '[[ "$PWD" == "$EXPECTED_PWD" && -z "$TMX_LEAK" ]] || exit 9; '
                                   'exit "$result"', EXPECTED_PWD=str(self.project))
        self.assert_ok(result)
        self.assertIn("hook failed", result.stderr)
        self.assertNotIn("unreachable", result.stdout)
        self.assertFalse((self.home / "wrong-hook").exists())
        self.real_tmux("has-session", "-t", "=failed-hook")
        self.assertEqual(self.commands()[-1][0], "attach-session")
        result = self.run_tmx("failed-hook", XDG_CONFIG_HOME=str(xdg))
        self.assert_ok(result)
        self.assertNotIn("hook failed", result.stderr)

    def test_creation_failure_and_invalid_directory_do_not_run_hook(self):
        self.hook('print ran > "$HOME/hook-ran"\n')
        for args, env in ((("bad-dir", "/missing/location"), {}),
                          (("empty-dir", ""), {}),
                          (("bad-create",), {"TMX_TEST_FAIL_CREATE": "1"})):
            with self.subTest(args=args):
                result = self.run_tmx(*args, **env)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "hook-ran").exists())
        self.assertFalse(any(cmd[0] == "attach-session" for cmd in self.commands()))

    def test_switch_inside_tmux_and_attach_exit_status(self):
        self.real_tmux("new-session", "-d", "-s", "current", "-x", "180", "-y", "45")
        pane = self.real_tmux("display-message", "-p", "-t", "=current:", "#{pane_id}")
        # A private-server context, not any inherited host TMUX/TMUX_PANE.
        inside = {"TMUX": f"{self.socket},0,0", "TMUX_PANE": pane}
        self.assert_ok(self.run_tmx("inside", **inside))
        self.assertEqual(self.commands()[-1][0], "switch-client")
        self.assertEqual(self.real_tmux("display-message", "-p", "-t", "=inside:",
                                       "#{window_width} #{window_height}"), "180 45")
        self.assert_ok(self.run_tmx("inside", **inside))
        result = self.run_tmx("inside", TMX_TEST_ATTACH_RESULT="7")
        self.assertEqual(result.returncode, 7)

    def test_zero_terminal_dimensions_have_positive_fallbacks(self):
        (self.bin / "tput").write_text("#!/bin/sh\nprintf '0\\n'\n")
        (self.bin / "tput").chmod(0o755)
        self.assert_ok(self.run_tmx("zero-size", COLUMNS="0", LINES="0"))
        dimensions = self.real_tmux("display-message", "-p", "-t", "=zero-size:",
                                    "#{window_width} #{window_height}")
        self.assertTrue(all(int(value) > 0 for value in dimensions.split()), dimensions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
