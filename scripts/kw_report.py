#!/usr/bin/env python3
"""Build a run report from Claude Code's own session transcripts.

  kw_report.py [--cwd DIR] [--session FILE] [--out RUN_DIR]

Finds the newest session transcript for DIR (default: current folder), reads the
main session and every subagent transcript, and writes into RUN_DIR:
  run-report.md        summary: totals, per-subagent table, checks, denials
  run-timeline.log     plain-text timeline, one line per event

RUN_DIR defaults to the newest <cwd>/.workflow/<run> or <cwd>/*/.workflow/<run>
folder, else <cwd>/.workflow. Read-only on transcripts; no network; no secrets
are copied (commands are truncated, tool results are never read).
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys


def local(ts):
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


def load(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def project_dir(cwd):
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd)))


def newest_session(cwd):
    files = glob.glob(os.path.join(project_dir(cwd), "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def find_run_dir(cwd):
    cands = glob.glob(os.path.join(cwd, ".workflow", "*", "state.json")) + glob.glob(os.path.join(cwd, "*", ".workflow", "*", "state.json"))
    if cands:
        return os.path.dirname(max(cands, key=os.path.getmtime))
    return os.path.join(cwd, ".workflow")


def text_of(content):
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in (content or []) if isinstance(c, dict) and c.get("type") == "text")


def short(s, n=110):
    s = re.sub(r"\s+", " ", s or "").strip()
    s = re.sub(r"(ghp_|sk-|xox[bp]-)[A-Za-z0-9_-]+", r"\1***", s)
    s = re.sub(r"(?i)(password|token|secret|api[_-]?key)(\s*[=:]\s*)\S+", r"\1\2***", s)
    return s if len(s) <= n else s[: n - 1] + "…"


def analyze(events):
    """Return stats for one transcript (main or subagent)."""
    a = [e for e in events if e.get("type") == "assistant"]
    tools, written, cmds = collections.Counter(), [], []
    tin = tout = cread = ccreate = 0
    for e in a:
        m = e.get("message", {})
        u = m.get("usage", {}) or {}
        tin += u.get("input_tokens", 0)
        tout += u.get("output_tokens", 0)
        cread += u.get("cache_read_input_tokens", 0)
        ccreate += u.get("cache_creation_input_tokens", 0)
        for c in m.get("content", []) or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tools[c["name"]] += 1
                inp = c.get("input", {}) or {}
                if c["name"] in ("Write", "Edit", "NotebookEdit"):
                    written.append(os.path.basename(str(inp.get("file_path", "?"))))
                if c["name"] in ("Bash", "PowerShell"):
                    cmds.append(short(str(inp.get("command", "")), 90))
    ts = [local(e["timestamp"]) for e in events if e.get("timestamp")]
    ts = [t for t in ts if t]
    denials = [e.get("toolDenialKind") for e in events if e.get("toolDenialKind")]
    final = ""
    for e in reversed(a):
        t = text_of(e.get("message", {}).get("content"))
        if t.strip():
            final = t
            break
    return dict(api=len(a), tools=tools, written=sorted(set(written)), cmds=cmds, tin=tin, tout=tout, cread=cread,
                ccreate=ccreate, start=min(ts) if ts else None, end=max(ts) if ts else None, denials=denials, final=final)


def fmt_t(t):
    return t.strftime("%H:%M:%S") if t else "?"


def secs(a, b):
    return int((b - a).total_seconds()) if a and b else 0


def fmt_n(n):
    return f"{n:,}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--session")
    ap.add_argument("--out")
    a = ap.parse_args()
    cwd = os.path.abspath(a.cwd)
    session = a.session or newest_session(cwd)
    if not session or not os.path.exists(session):
        print(f"No session transcript found for {cwd} (looked in {project_dir(cwd)}).")
        return 1
    out = a.out or find_run_dir(cwd)
    os.makedirs(out, exist_ok=True)

    main_ev = load(session)
    sess_id = os.path.splitext(os.path.basename(session))[0]
    sub_dir = os.path.join(os.path.dirname(session), sess_id, "subagents")

    # --- launches in the main transcript (Agent/Task tool calls), in order
    launches = []
    for e in main_ev:
        if e.get("type") == "assistant":
            for c in e.get("message", {}).get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                    launches.append(dict(id=c["id"], ts=local(e.get("timestamp", "")), inp=c.get("input", {}) or {}))
    meta = {}
    for mf in glob.glob(os.path.join(sub_dir, "*.meta.json")):
        try:
            m = json.load(open(mf, encoding="utf-8"))
            meta[m.get("toolUseId")] = (os.path.basename(mf).replace(".meta.json", ""), m)
        except Exception:
            pass

    subs = []
    for i, L in enumerate(launches, 1):
        base, m = meta.get(L["id"], (None, {}))
        st = analyze(load(os.path.join(sub_dir, base + ".jsonl"))) if base and os.path.exists(os.path.join(sub_dir, base + ".jsonl")) else None
        prompt = str(L["inp"].get("prompt", ""))
        agent = str(L["inp"].get("subagent_type") or m.get("agentType") or "?")
        status = ""
        if st:
            mm = re.search(r"(?im)^\W*-?\s*\**Status\**\s*:\s*\**\s*([A-Z_ ]+[A-Z])", st["final"])
            status = mm.group(1).strip() if mm else ""
            vm = re.search(r"(?i)verdict\W+(approved with follow-ups|approved|blocked)", st["final"])
            if vm:
                status = (status + " / " if status else "") + vm.group(1).upper()
        subs.append(dict(n=i, agent=agent, short=agent.split(":")[-1], desc=str(L["inp"].get("description", "")), st=st, prompt=prompt, status=status, launched=L["ts"]))

    main_st = analyze([e for e in main_ev if not e.get("isSidechain")])
    cost = next((e for e in main_ev if e.get("type") == "cost-state"), None)
    attr = next(({k: e[k] for k in ("attributionSkill", "attributionPlugin") if k in e} for e in main_ev if e.get("attributionSkill")), {})
    versions = sorted({e.get("version") for e in main_ev if e.get("version")})

    # --- semantic history from state.json, if the orchestrator kept one
    hist = []
    sj = os.path.join(out, "state.json")
    if os.path.exists(sj):
        try:
            hist = json.load(open(sj, encoding="utf-8")).get("history", []) or []
        except Exception:
            pass

    # --- checks
    checks = []
    coders = [s for s in subs if s["short"] == "ai-coding-agent"]
    for s in coders + [s for s in subs if s["short"] == "deployment-devops-agent"]:
        ok = bool(re.search(r"approved\s*:", s["prompt"], re.I))
        checks.append((ok, f"#{s['n']} {s['short']} prompt contains `approved:`" + ("" if ok else "  <- no approval text in the prompt")))
    for i, x in enumerate(coders):
        for y in coders[i + 1:]:
            if x["st"] and y["st"] and x["st"]["start"] and y["st"]["start"] and y["st"]["start"] < x["st"]["end"]:
                checks.append((True, f"ran in parallel: #{x['n']} and #{y['n']} ({x['desc']} / {y['desc']})"))
    n_coders, n_rev = len(coders), len([s for s in subs if s["short"] == "code-reviewer"])
    checks.append((True, f"coding runs: {n_coders}, reviewer runs: {n_rev}"))
    total_den = sum(len(s["st"]["denials"]) for s in subs if s["st"]) + len(main_st["denials"])
    where = [f"#{s['n']} {s['short']} x{len(s['st']['denials'])} ({', '.join(sorted(set(map(str, s['st']['denials']))))})"
             for s in subs if s["st"] and s["st"]["denials"]]
    if main_st["denials"]:
        where.append(f"orchestrator x{len(main_st['denials'])} ({', '.join(sorted(set(map(str, main_st['denials']))))})")
    checks.append((total_den == 0, f"permission denials: {total_den}" + (": " + "; ".join(where) if where else "")))
    no_tx = [s["n"] for s in subs if not s["st"]]
    if no_tx:
        checks.append((False, f"no transcript found for subagent(s): {no_tx}"))

    # --- timeline log
    rows = []
    if main_st["start"]:
        rows.append((main_st["start"], f"SESSION  start  skill={attr.get('attributionSkill', '-')} plugin={attr.get('attributionPlugin', '-')} cc={','.join(versions)}"))
    for s in subs:
        st = s["st"]
        if s["launched"]:
            rows.append((s["launched"], f"LAUNCH   #{s['n']:<2} {s['short']:<24} {s['desc']}"))
        if st:
            rows.append((st["start"], f"START    #{s['n']:<2} {s['short']}"))
            for w in st["written"]:
                rows.append((st["end"], f"WROTE    #{s['n']:<2} {s['short']:<24} {w}"))
            rows.append((st["end"], f"END      #{s['n']:<2} {s['short']:<24} {secs(st['start'], st['end'])}s api={st['api']} tools={dict(st['tools'])} out={fmt_n(st['tout'])}tok status={s['status'] or '-'}"))
    for h in hist:
        rows.append((local(h.get("ts", "")) or main_st["start"], f"STAGE    {h.get('stage', '?')} {h.get('agent', '')} status={h.get('status', '')} verdict={h.get('verdict', '')} {h.get('note', '')}"))
    if main_st["end"]:
        rows.append((main_st["end"], "SESSION  end"))
    rows = [r for r in rows if r[0]]
    rows.sort(key=lambda r: r[0])
    with open(os.path.join(out, "run-timeline.log"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# run timeline from {os.path.basename(session)} (local time)\n")
        for t, line in rows:
            f.write(f"{fmt_t(t)}  {line}\n")

    # --- markdown report
    tot_out = main_st["tout"] + sum(s["st"]["tout"] for s in subs if s["st"])
    tot_read = main_st["cread"] + sum(s["st"]["cread"] for s in subs if s["st"])
    tot_new = main_st["tin"] + main_st["ccreate"] + sum(s["st"]["tin"] + s["st"]["ccreate"] for s in subs if s["st"])
    L = []
    L.append(f"# Run report\n\nSession `{sess_id}`  |  cwd `{cwd}`  |  Claude Code {','.join(versions)}")
    if attr:
        L.append(f"Triggered by skill `{attr.get('attributionSkill', '-')}` from plugin `{attr.get('attributionPlugin', '-')}`.")
    dur = secs(main_st["start"], main_st["end"])
    L.append(f"\n## Totals\n\n- Wall clock: {dur // 60}m {dur % 60}s ({fmt_t(main_st['start'])} to {fmt_t(main_st['end'])})")
    L.append(f"- Subagent calls: {len(subs)}  ({', '.join(f'{k} x{v}' for k, v in collections.Counter(s['short'] for s in subs).most_common())})")
    L.append(f"- Output tokens: {fmt_n(tot_out)}; fresh input tokens (incl. cache writes): {fmt_n(tot_new)}; cache-read tokens: {fmt_n(tot_read)}")
    if cost:
        L.append(f"- Session cost reported by Claude Code: ${cost.get('totalCostUSD', 0):.2f} (API time {int((cost.get('totalAPIDuration', 0) or 0) / 1000)}s)")
    else:
        L.append("- Cost: not in this transcript (interactive sessions do not record it); token totals above are exact.")
    L.append(f"- Orchestrator (main session): {main_st['api']} model turns, tools {dict(main_st['tools'])}, {fmt_n(main_st['tout'])} output tokens")
    L.append("\n## Subagents\n\n| # | Agent | What | Start | Secs | Turns | Tools | Out tok | Wrote | Status |\n|---|---|---|---|---|---|---|---|---|---|")
    for s in subs:
        st = s["st"]
        if st:
            L.append(f"| {s['n']} | {s['short']} | {s['desc']} | {fmt_t(st['start'])} | {secs(st['start'], st['end'])} | {st['api']} | {', '.join(f'{k} {v}' for k, v in st['tools'].most_common())} | {fmt_n(st['tout'])} | {', '.join(st['written']) or '-'} | {s['status'] or '-'} |")
        else:
            L.append(f"| {s['n']} | {s['short']} | {s['desc']} | ? | ? | ? | ? | ? | ? | no transcript |")
    L.append("\n## Checks\n")
    for ok, msg in checks:
        L.append(f"- [{'x' if ok else ' '}] {msg}")
    cmds = [(s["n"], s["short"], c) for s in subs if s["st"] for c in s["st"]["cmds"]]
    if cmds:
        L.append("\n## Shell commands run by subagents (truncated)\n")
        for n, sname, c in cmds[:40]:
            L.append(f"- #{n} {sname}: `{c}`")
        if len(cmds) > 40:
            L.append(f"- ... and {len(cmds) - 40} more")
    if hist:
        L.append("\n## Stage history (from state.json)\n")
        for h in hist:
            L.append(f"- {h.get('ts', '')} {h.get('stage', '')} {h.get('agent', '')} {h.get('status', '')} {h.get('verdict', '')}")
    L.append("\n_Generated from Claude Code transcripts; tool results and file contents are never copied. See run-timeline.log for the event-by-event view._\n")
    with open(os.path.join(out, "run-report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print(f"wrote {os.path.join(out, 'run-report.md')} and run-timeline.log ({len(subs)} subagents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
