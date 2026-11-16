#!/usr/bin/env python3
"""Check that the Claude settings merge keeps local keys and replaces old links."""

import json
from pathlib import Path
import os
import sys
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/setup-claude-settings.py"
BASE = json.loads((ROOT / "packages/claude/settings.base.json").read_text())


class ClaudeSettingsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="claude-settings-")
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.dest = self.home / ".claude/settings.json"

    def merge(self):
        subprocess.run([sys.executable, str(SCRIPT)], env={**os.environ, "HOME": str(self.home)}, check=True)
        return json.loads(self.dest.read_text())

    def test_baseline_wins_and_local_keys_survive_reruns(self):
        self.dest.parent.mkdir()
        self.dest.write_text(json.dumps({"theme": "light", "model": "opus"}))
        for _ in range(2):
            merged = self.merge()
            self.assertEqual(merged["theme"], "light")
            self.assertEqual(merged["model"], BASE["model"])
            self.assertEqual(merged["permissions"], BASE["permissions"])
        self.assertFalse(list(self.dest.parent.glob("settings.json.*")))

    def test_old_link_into_repo_becomes_a_real_file_without_touching_the_repo(self):
        repo = self.home / "repo-settings.json"
        repo.write_text(json.dumps({"theme": "dark"}))
        self.dest.parent.mkdir()
        self.dest.symlink_to(repo)
        self.assertEqual(self.merge()["theme"], "dark")
        self.assertFalse(self.dest.is_symlink())
        self.assertEqual(json.loads(repo.read_text()), {"theme": "dark"})

    def test_dangling_link_and_missing_file_start_from_baseline(self):
        self.dest.parent.mkdir()
        self.dest.symlink_to(self.home / "gone.json")
        self.assertEqual(self.merge(), BASE)
        self.dest.unlink()
        self.assertEqual(self.merge(), BASE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
