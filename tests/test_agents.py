"""Static checks on agent definitions. A plugin-loaded agent was observed to ignore the `tools`
allowlist (probe wrote a file), while `disallowedTools` held. So every agent that must not have a
capability has to deny it explicitly. See docs/EVIDENCE.md, "Tool-grant probes"."""
import re
import unittest
from pathlib import Path

AGENTS = sorted((Path(__file__).resolve().parent.parent / "agents").glob("*.md"))
WRITERS = {"Write", "Edit", "NotebookEdit"}
SHELLS = {"Bash", "PowerShell"}


def parse(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path.name}: no frontmatter"
    fm = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


def names(v):
    return {x.strip() for x in v.split(",") if x.strip()}


class AgentDefinitions(unittest.TestCase):
    def test_count_and_required_fields(self):
        self.assertEqual(len(AGENTS), 15)
        for p in AGENTS:
            fm = parse(p)
            for k in ("name", "description", "tools", "model"):
                self.assertTrue(fm.get(k), f"{p.name} missing {k}")
            self.assertEqual(fm["name"], p.stem)

    def test_every_capability_not_granted_is_explicitly_denied(self):
        """Agents without file-write tools must deny them; agents without a shell must deny the shell."""
        for p in AGENTS:
            fm = parse(p)
            tools, deny = names(fm["tools"]), names(fm.get("disallowedTools", ""))
            if p.stem in ("ai-coding-agent", "unit-test-agent", "qa-agent"):
                continue  # these three are the ones allowed to edit files and run commands
            for t in sorted(WRITERS - tools):
                self.assertIn(t, deny, f"{p.name} is not granted {t} but does not deny it")
            if not (tools & SHELLS):
                for t in sorted(SHELLS):
                    self.assertIn(t, deny, f"{p.name} has no shell but does not deny {t}")

    def test_never_deny_what_is_granted(self):
        for p in AGENTS:
            fm = parse(p)
            self.assertFalse(names(fm["tools"]) & names(fm.get("disallowedTools", "")), p.name)

    def test_only_three_agents_can_edit_source(self):
        editors = sorted(p.stem for p in AGENTS if "Edit" in names(parse(p)["tools"]))
        self.assertEqual(editors, ["ai-coding-agent", "qa-agent", "unit-test-agent"])

    def test_no_connector_tool_names(self):
        for p in AGENTS:
            self.assertNotIn("mcp__", p.read_text(encoding="utf-8"), p.name)


if __name__ == "__main__":
    unittest.main()
