"""Installer tests (project scope in a temp dir; never touches ~/.claude)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "install" / "kw_install.py"
N_AGENTS = len(list((ROOT / "agents").glob("*.md")))


def run(cwd, *args):
    return subprocess.run([sys.executable, "-I", str(INSTALLER), *args, "--scope", "project"],
                          cwd=cwd, text=True, capture_output=True)


class Installer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.base = self.cwd / ".claude"
        self.addCleanup(self.tmp.cleanup)

    def test_install_and_uninstall_roundtrip(self):
        r = run(self.cwd, "install")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(list((self.base / "agents").glob("*.md"))), N_AGENTS)
        skill = (self.base / "skills" / "dev-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", skill)
        self.assertFalse((self.base / "settings.json").exists(), "guardrail must be opt-in")
        r = run(self.cwd, "uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list((self.base / "agents").glob("*.md")), [])
        self.assertFalse((self.base / "skills" / "dev-workflow").exists())

    def test_user_agent_is_backed_up_and_restored(self):
        (self.base / "agents").mkdir(parents=True)
        mine = self.base / "agents" / "code-reviewer.md"
        mine.write_text("MY OWN AGENT", encoding="utf-8")
        run(self.cwd, "install")
        self.assertIn("KnowledgeWala", mine.read_text(encoding="utf-8"))
        self.assertEqual((self.base / "agents" / "code-reviewer.md.user-backup").read_text(), "MY OWN AGENT")
        run(self.cwd, "uninstall")
        self.assertEqual(mine.read_text(encoding="utf-8"), "MY OWN AGENT")

    def test_reinstall_is_idempotent_and_keeps_backup(self):
        (self.base / "agents").mkdir(parents=True)
        (self.base / "agents" / "qa-agent.md").write_text("MINE", encoding="utf-8")
        run(self.cwd, "install")
        run(self.cwd, "install")
        run(self.cwd, "uninstall")
        self.assertEqual((self.base / "agents" / "qa-agent.md").read_text(), "MINE")

    def test_guardrail_merge_preserves_settings_and_removes_cleanly(self):
        self.base.mkdir()
        original = {"model": "sonnet", "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo x"}]}]}}
        (self.base / "settings.json").write_text(json.dumps(original), encoding="utf-8")
        self.assertEqual(run(self.cwd, "guardrail", "on").returncode, 0)
        data = json.loads((self.base / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 2)
        self.assertEqual(data["model"], "sonnet")
        run(self.cwd, "guardrail", "on")  # idempotent
        self.assertEqual(len(json.loads((self.base / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]), 2)
        run(self.cwd, "guardrail", "off")
        self.assertEqual(json.loads((self.base / "settings.json").read_text(encoding="utf-8")), original)

    def test_unparseable_settings_is_left_untouched(self):
        self.base.mkdir()
        text = '{\n  // my comment\n  "model": "sonnet",\n}\n'
        (self.base / "settings.json").write_text(text, encoding="utf-8")
        r = run(self.cwd, "guardrail", "on")
        self.assertEqual((self.base / "settings.json").read_text(encoding="utf-8"), text)
        self.assertIn("Not modified", r.stdout)

    def test_bom_settings_is_handled(self):
        self.base.mkdir()
        (self.base / "settings.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"model": "opus"}).encode())
        self.assertEqual(run(self.cwd, "guardrail", "on").returncode, 0)
        self.assertEqual(json.loads((self.base / "settings.json").read_text(encoding="utf-8"))["model"], "opus")


if __name__ == "__main__":
    unittest.main()
