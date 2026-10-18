"""Tests for the live logger (kw_trace.py), the observe hook installer and the report (kw_report.py)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "scripts" / "kw_trace.py"
REPORT = ROOT / "scripts" / "kw_report.py"
INSTALLER = ROOT / "install" / "kw_install.py"
EVENTS = {"SubagentStart", "SubagentStop", "PostToolUse", "PostToolUseFailure", "PermissionDenied", "Stop"}


def trace(payload):
    return subprocess.run([sys.executable, "-I", str(TRACE)], input=payload if isinstance(payload, str) else json.dumps(payload),
                          text=True, capture_output=True)


class Trace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def make_run(self):
        run = self.cwd / "app" / ".workflow" / "20261018-demo"
        run.mkdir(parents=True)
        (run / "state.json").write_text("{}", encoding="utf-8")
        return run

    def test_logs_inside_a_workflow_run(self):
        run = self.make_run()
        r = trace({"hook_event_name": "SubagentStart", "cwd": str(self.cwd), "agent_id": "abcdef123456", "agent_type": "knowledgewala-agentic-sdlc:security-agent"})
        self.assertEqual((r.returncode, r.stdout), (0, ""), "must never print to stdout")
        trace({"hook_event_name": "PostToolUse", "cwd": str(self.cwd), "agent_type": "security-agent", "tool_name": "Write",
               "tool_input": {"file_path": "C:/x/y/report.md", "content": "SECRET BODY"}})
        trace({"hook_event_name": "SubagentStop", "cwd": str(self.cwd), "agent_id": "abcdef123456", "agent_type": "security-agent",
               "last_assistant_message": "Status: READY"})
        log = (run / "run.log").read_text(encoding="utf-8")
        self.assertIn("START", log)
        self.assertIn("security-agent", log)
        self.assertIn("report.md", log)
        self.assertNotIn("SECRET BODY", log, "file contents must never be logged")
        self.assertIn("Status: READY", log)
        lines = [json.loads(x) for x in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([x["event"] for x in lines], ["SubagentStart", "PostToolUse", "SubagentStop"])

    def test_noop_outside_a_workflow(self):
        r = trace({"hook_event_name": "PostToolUse", "cwd": str(self.cwd), "tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(list(self.cwd.iterdir()), [], "must not create files in unrelated projects")

    def test_our_agent_without_a_run_folder_creates_one(self):
        trace({"hook_event_name": "SubagentStart", "cwd": str(self.cwd), "agent_type": "knowledgewala-agentic-sdlc:qa-agent"})
        self.assertTrue((self.cwd / ".workflow" / "run.log").exists())

    def test_secrets_are_masked_and_commands_truncated(self):
        run = self.make_run()
        cmd = "curl -H 'Authorization: Bearer abc123SECRET' https://x --token=ghp_ABCDEFsecret " + "x" * 400
        trace({"hook_event_name": "PostToolUse", "cwd": str(self.cwd), "tool_name": "Bash", "tool_input": {"command": cmd}})
        log = (run / "run.log").read_text(encoding="utf-8")
        self.assertNotIn("abc123SECRET", log)
        self.assertNotIn("ghp_ABCDEFsecret", log)
        self.assertLess(max(len(x) for x in log.splitlines()), 220)

    def test_nonexistent_cwd_creates_nothing(self):
        ghost = self.cwd / "does" / "not" / "exist"
        r = trace({"hook_event_name": "SubagentStart", "cwd": str(ghost), "agent_type": "security-agent"})
        self.assertEqual(r.returncode, 0)
        self.assertFalse((self.cwd / "does").exists())

    def test_tool_duration_is_logged(self):
        run = self.make_run()
        trace({"hook_event_name": "PostToolUse", "cwd": str(self.cwd), "agent_type": "qa-agent", "tool_name": "Read",
               "tool_input": {"file_path": "a/b.txt"}, "duration_ms": 42})
        self.assertIn("(42ms)", (run / "run.log").read_text(encoding="utf-8"))

    def test_bad_input_never_fails(self):
        for bad in ("", "not json", "[]", '{"hook_event_name": 5}', "null"):
            self.assertEqual(trace(bad).returncode, 0, bad)


class ObserveInstall(unittest.TestCase):
    def run_inst(self, cwd, *args):
        return subprocess.run([sys.executable, "-I", str(INSTALLER), *args, "--scope", "project"], cwd=cwd, text=True, capture_output=True)

    def test_observe_on_off_roundtrip_preserves_other_hooks(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / ".claude"
            base.mkdir()
            original = {"hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo mine"}]}]}, "model": "sonnet"}
            (base / "settings.json").write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(self.run_inst(t, "observe", "on").returncode, 0)
            data = json.loads((base / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(set(data["hooks"]), EVENTS)
            self.assertEqual(len(data["hooks"]["PostToolUse"]), 2)
            self.run_inst(t, "observe", "on")  # idempotent
            self.assertEqual(len(json.loads((base / "settings.json").read_text(encoding="utf-8"))["hooks"]["PostToolUse"]), 2)
            self.run_inst(t, "observe", "off")
            self.assertEqual(json.loads((base / "settings.json").read_text(encoding="utf-8")), original)

    def test_uninstall_removes_both_hooks(self):
        with tempfile.TemporaryDirectory() as t:
            self.run_inst(t, "install", "--guardrail", "--observe")
            data = json.loads((Path(t) / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertIn("PreToolUse", data["hooks"])
            self.assertIn("SubagentStop", data["hooks"])
            self.assertTrue((Path(t) / ".claude" / "knowledgewala" / "kw_report.py").exists())
            self.run_inst(t, "uninstall")
            self.assertFalse((Path(t) / ".claude" / "settings.json").read_text(encoding="utf-8").count("kw_trace"))
            self.assertFalse((Path(t) / ".claude" / "knowledgewala").exists())


class Report(unittest.TestCase):
    def test_report_from_fixture_transcripts(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as proj:
            import re
            pdir = Path(home) / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(proj))
            sid = "11111111-2222-3333-4444-555555555555"
            (pdir / sid / "subagents").mkdir(parents=True)

            def ev(t, ts, **kw):
                return json.dumps({"type": t, "timestamp": ts, "sessionId": sid, **kw})

            def asst(ts, content, out=100):
                return ev("assistant", ts, message={"content": content, "usage": {"input_tokens": 1, "output_tokens": out,
                          "cache_read_input_tokens": 50, "cache_creation_input_tokens": 10}})
            main = [
                asst("2026-10-18T10:00:00Z", [{"type": "tool_use", "id": "tu1", "name": "Agent",
                     "input": {"subagent_type": "knowledgewala-agentic-sdlc:ai-coding-agent", "description": "Implement T1", "prompt": "approved: implement T1"}}]),
                asst("2026-10-18T10:00:30Z", [{"type": "tool_use", "id": "tu2", "name": "Agent",
                     "input": {"subagent_type": "knowledgewala-agentic-sdlc:ai-coding-agent", "description": "Implement T2", "prompt": "just do it"}}]),
                ev("user", "2026-10-18T10:00:40Z", toolDenialKind="user-rejected"),
                json.dumps({"type": "cost-state", "totalCostUSD": 1.5, "totalAPIDuration": 12000}),
            ]
            (pdir / f"{sid}.jsonl").write_text("\n".join(main), encoding="utf-8")
            for aid, tu, start, end in (("a1", "tu1", "10:00:05", "10:00:25"), ("a2", "tu2", "10:00:35", "10:00:55")):
                body = [asst(f"2026-10-18T{start}Z", [{"type": "tool_use", "id": "x", "name": "Write", "input": {"file_path": "C:/p/app.py"}}]),
                        asst(f"2026-10-18T{end}Z", [{"type": "text", "text": "Done.\n## Handoff\n- Status: READY\n"}])]
                (pdir / sid / "subagents" / f"agent-{aid}.jsonl").write_text("\n".join(body), encoding="utf-8")
                (pdir / sid / "subagents" / f"agent-{aid}.meta.json").write_text(json.dumps({"toolUseId": tu, "agentType": "x"}), encoding="utf-8")
            out = Path(proj) / ".workflow" / "run1"
            env = {**os.environ, "USERPROFILE": home, "HOME": home}
            r = subprocess.run([sys.executable, "-I", str(REPORT), "--cwd", proj, "--out", str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            rep = (out / "run-report.md").read_text(encoding="utf-8")
            self.assertIn("Subagent calls: 2", rep)
            self.assertIn("$1.50", rep)
            self.assertIn("API time 12s", rep, "API duration is milliseconds")
            self.assertIn("app.py", rep)
            self.assertIn("READY", rep)
            self.assertIn("[x] #1 ai-coding-agent prompt contains `approved:`", rep)
            self.assertIn("[ ] #2 ai-coding-agent prompt contains `approved:`", rep, "missing approval text must be flagged")
            self.assertIn("permission denials: 1", rep)
            self.assertIn("user-rejected", rep)
            tl = (out / "run-timeline.log").read_text(encoding="utf-8")
            self.assertIn("WROTE", tl)
            self.assertIn("ai-coding-agent", tl)

    def test_no_transcript_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as proj:
            env = {**os.environ, "USERPROFILE": home, "HOME": home}
            r = subprocess.run([sys.executable, "-I", str(REPORT), "--cwd", proj], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("No session transcript", r.stdout)


if __name__ == "__main__":
    unittest.main()
