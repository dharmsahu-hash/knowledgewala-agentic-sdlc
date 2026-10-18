#!/usr/bin/env python3
"""Live run logger (opt-in hook): writes run.log and events.jsonl into the run folder.

Registered by `kw_install.py observe on` for: SubagentStart, SubagentStop,
PostToolUse, PostToolUseFailure, PermissionDenied, Stop.

Design rules
- Never break a run: every error is swallowed, exit code is always 0.
- Print NOTHING to stdout (hook stdout can be injected into the model's context).
- Only act inside a workflow: a <cwd>/.workflow/<run>/ folder exists, or the
  event comes from one of this package's agents. Otherwise do nothing.
- Log what happened, not content: tool name, a short target (file name, truncated
  command, pattern), agent, timing. Tool results are never read. Obvious secrets
  are masked. Files stop growing at 5 MB.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

OURS = {"ticket-analyst", "business-analyst", "requirement-analyst", "solution-architect", "task-planner",
        "ai-coding-agent", "unit-test-agent", "security-agent", "performance-agent", "code-reviewer",
        "documentation-generator", "qa-agent", "deploy-planner", "deployment-devops-agent", "ops-monitor"}
MAX_BYTES = 5 * 1024 * 1024


def short(s, n=110):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = re.sub(r"(ghp_|sk-|xox[bp]-|AKIA)[A-Za-z0-9_-]+", r"\1***", s)
    s = re.sub(r"(?i)(password|passwd|token|secret|api[_-]?key|authorization)(\s*[=:]\s*)(bearer\s+)?\S+", r"\1\2***", s)
    return s if len(s) <= n else s[: n - 1] + "…"


def find_run_dir(cwd):
    pats = [os.path.join(cwd, ".workflow", "*", "state.json"), os.path.join(cwd, "*", ".workflow", "*", "state.json")]
    c = [p for pat in pats for p in glob.glob(pat)]
    return os.path.dirname(max(c, key=os.path.getmtime)) if c else None


def detail(tool, inp):
    inp = inp or {}
    if tool in ("Write", "Edit", "Read", "NotebookEdit"):
        return os.path.basename(str(inp.get("file_path", "")))
    if tool in ("Bash", "PowerShell"):
        return short(inp.get("command", ""), 100)
    if tool in ("Grep", "Glob"):
        return short(inp.get("pattern", ""), 60)
    if tool in ("Agent", "Task"):
        return f"{str(inp.get('subagent_type', '')).split(':')[-1]} - {short(inp.get('description', ''), 60)}"
    return ""


def append(path, text):
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            return
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except Exception:
        pass


def main():
    p = json.load(sys.stdin)
    event = p.get("hook_event_name", "")
    cwd = p.get("cwd") or os.getcwd()
    if not os.path.isdir(cwd):
        return  # never create a folder tree for a path that does not exist
    agent = str(p.get("agent_type") or "").split(":")[-1]
    run_dir = find_run_dir(cwd)
    if not run_dir and agent not in OURS:
        return
    if not run_dir:
        run_dir = os.path.join(cwd, ".workflow")
    os.makedirs(run_dir, exist_ok=True)

    who = agent or "orchestrator"
    aid = str(p.get("agent_id") or "")[:8]
    tool = p.get("tool_name", "")
    if event == "SubagentStart":
        label, text = "START", f"{who} id={aid}"
    elif event == "SubagentStop":
        label, text = "END", f"{who} id={aid} | {short(p.get('last_assistant_message', ''), 140)}"
    elif event == "PostToolUse":
        ms = p.get("duration_ms")
        label, text = "TOOL", f"{who:<22} {tool:<10} {detail(tool, p.get('tool_input'))}" + (f"  ({int(ms)}ms)" if isinstance(ms, (int, float)) else "")
    elif event == "PostToolUseFailure":
        label, text = "FAIL", f"{who:<22} {tool:<10} {detail(tool, p.get('tool_input'))} | {short(p.get('error', ''), 80)}"
    elif event == "PermissionDenied":
        label, text = "DENIED", f"{who:<22} {tool:<10} {detail(tool, p.get('tool_input'))}"
    elif event == "Stop":
        label, text = "STOP", "main session turn ended"
    else:
        return
    now = dt.datetime.now()
    append(os.path.join(run_dir, "run.log"), f"{now:%H:%M:%S}  {label:<7} {text}\n")
    append(os.path.join(run_dir, "events.jsonl"), json.dumps({
        "ts": now.isoformat(timespec="seconds"), "event": event, "agent": who, "agent_id": aid, "tool": tool,
        "detail": detail(tool, p.get("tool_input")) if tool else "", "session": str(p.get("session_id", ""))[:8],
        "payload_keys": sorted(p.keys())}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
