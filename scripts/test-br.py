#!/usr/bin/env python3
"""Exercise Zsh brightness helpers without accessing real monitors."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "requires Zsh")
class BrightnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="br-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.log = self.home / "commands.jsonl"
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(self.bin),
                    "BR_TEST_LOG": str(self.log)}
        mock = self.bin / "ddcutil"
        mock.write_text(f"#!{sys.executable}\n" + '''
import json
import os
import sys
args = sys.argv[1:]
with open(os.environ["BR_TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[1] == os.environ.get("BR_TEST_FAIL_DISPLAY"):
    print("simulated display failure", file=sys.stderr)
    sys.exit(1)
if args[2] == "getvcp":
    print("VCP code 0x10 (Brightness): current value = 40, max value = 100")
else:
    print("brightness set")
''')
        mock.chmod(0o755)
        source = (ROOT / "packages/zshrc/.zshrc").read_text()
        self.functions = self.home / "brightness.zsh"
        self.functions.write_text("# ddcutil brightness helpers" + source.split(
            "# ddcutil brightness helpers", 1)[1].split(
            "# Cross-platform open command", 1)[0])

    def run_br(self, *args, code='"$@"', **env):
        return subprocess.run([ZSH, "-f", "-c", 'source "$1"; shift; ' + code,
                               "br-check", str(self.functions), *args],
                              env={**self.env, **env}, text=True,
                              capture_output=True, timeout=10)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_loading_does_not_access_monitors(self):
        result = self.run_br(code='(( ${+functions[br]} && ${+functions[br1]} && ${+functions[br2]} ))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [])

    def test_no_helpers_without_ddcutil(self):
        result = self.run_br(PATH="/nonexistent", code='(( ! ${+functions[br]} && ! ${+functions[br1]} && ! ${+functions[br2]} ))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [])

    def test_read_both_displays(self):
        result = self.run_br("br")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [["--display", str(i), "getvcp", "10"] for i in (1, 2)])
        for display in (1, 2):
            self.assertIn(f"Display {display}:\nVCP", result.stdout)
        self.assertEqual(result.stdout.count("current value = 40, max value = 100"), 2)

    def test_read_individual_display(self):
        for display in (1, 2):
            with self.subTest(display=display):
                result = self.run_br(f"br{display}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.commands()[-1], ["--display", str(display), "getvcp", "10"])
                self.assertIn("current value = 40, max value = 100", result.stdout)

    def test_set_both_displays_remains_quiet(self):
        result = self.run_br("br", "50")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(self.commands()), [["--display", str(i), "setvcp", "10", "50"] for i in (1, 2)])
        self.assertEqual(result.stdout, "")

    def test_set_individual_display(self):
        for display in (1, 2):
            with self.subTest(display=display):
                result = self.run_br(f"br{display}", "50")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.commands()[-1], ["--display", str(display), "setvcp", "10", "50"])
                self.assertIn("brightness set", result.stdout)

    def test_read_failure_is_visible_and_other_display_still_queried(self):
        for display in (1, 2):
            with self.subTest(display=display):
                result = self.run_br("br", BR_TEST_FAIL_DISPLAY=str(display))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("simulated display failure", result.stderr)
                self.assertIn("current value = 40, max value = 100", result.stdout)
                self.assertEqual(self.commands()[-2:], [["--display", str(i), "getvcp", "10"] for i in (1, 2)])
                result = self.run_br(f"br{display}", BR_TEST_FAIL_DISPLAY=str(display))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("simulated display failure", result.stderr)


if __name__ == "__main__":
    unittest.main()
