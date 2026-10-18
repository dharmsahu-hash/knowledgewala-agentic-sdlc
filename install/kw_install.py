#!/usr/bin/env python3
"""KnowledgeWala Agentic SDLC installer (no plugin system needed).

  kw_install.py install   [--scope user|project] [--guardrail] [--observe]
  kw_install.py uninstall [--scope user|project]
  kw_install.py guardrail on|off [--scope user|project]
  kw_install.py observe   on|off [--scope user|project]

user scope    -> ~/.claude        (all projects)
project scope -> ./.claude        (current folder only)

Safe by design: existing agents with the same name are backed up (*.user-backup)
and restored on uninstall; a manifest records exactly what was installed; a
settings.json that cannot be parsed is never modified (you get a snippet to
paste instead); both hooks are OFF unless you ask for them.

guardrail  blocks obviously destructive shell commands (tripwire, not a sandbox)
observe    writes run.log + events.jsonl into the run folder as a workflow runs
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = "KnowledgeWala Agentic SDLC"

# feature -> script, and the hook events it registers (event -> matcher or None)
FEATURES = {
    "guardrail": {"script": "block_destructive.py", "events": {"PreToolUse": "Bash|PowerShell"}},
    "observe": {"script": "kw_trace.py", "events": {e: None for e in (
        "SubagentStart", "SubagentStop", "PostToolUse", "PostToolUseFailure", "PermissionDenied", "Stop")}},
}


def write_text(path, text):
    # Path.write_text(newline=...) needs Python 3.10+; open() works on 3.8+.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def base_dir(scope):
    return (Path.home() if scope == "user" else Path.cwd()) / ".claude"


def version():
    try:
        return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except Exception:
        return "unknown"


def load_settings(path):
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig").strip()
    return json.loads(text) if text else {}


def hook_command(script):
    p = Path(script).as_posix()
    return f'python3 "{p}" || python "{p}"'


def entry(script, matcher):
    e = {"hooks": [{"type": "command", "command": hook_command(script)}]}
    if matcher:
        e = {"matcher": matcher, **e}
    return e


def snippet(name, script):
    ev = FEATURES[name]["events"]
    return json.dumps({"hooks": {k: [entry(script, m)] for k, m in ev.items()}}, indent=2)


def edit_settings(base, name, script, add):
    marker = FEATURES[name]["script"]
    path = base / "settings.json"
    try:
        data = load_settings(path)
    except Exception as e:
        print(f"! Could not parse {path} ({e}).\n  Not modified. To enable '{name}' add this yourself:\n{snippet(name, script)}")
        return False
    hooks = data.setdefault("hooks", {})
    for event, matcher in FEATURES[name]["events"].items():
        lst = hooks.setdefault(event, [])
        ours = lambda e: any(marker in h.get("command", "") for h in e.get("hooks", []))
        if add:
            if not any(ours(e) for e in lst):
                lst.append(entry(script, matcher))
        else:
            hooks[event] = [e for e in lst if not ours(e)]
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        del data["hooks"]
    if path.exists() and not (base / "settings.json.kw-backup").exists():
        shutil.copy2(path, base / "settings.json.kw-backup")
    base.mkdir(parents=True, exist_ok=True)
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def feature(base, name, on):
    kw = base / "knowledgewala"
    script = kw / FEATURES[name]["script"]
    if on:
        kw.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts" / FEATURES[name]["script"], script)
        if edit_settings(base, name, script, True):
            print(f"{name} ON ({script}). Restart Claude Code.")
    else:
        edit_settings(base, name, script, False)
        if script.exists():
            script.unlink()
        print(f"{name} OFF")


def install(base, with_guardrail, with_observe):
    manifest_path = base / "knowledgewala" / "manifest.json"
    manifest = {"version": version(), "files": [], "backups": {}}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = version()

    def put(src, dst, transform=None):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and str(dst) not in manifest["files"]:
            if MARK not in dst.read_text(encoding="utf-8", errors="ignore"):
                bak = dst.with_name(dst.name + ".user-backup")
                shutil.copy2(dst, bak)
                manifest["backups"][str(dst)] = str(bak)
                print(f"  backed up your existing {dst.name} -> {bak.name}")
        text = src.read_text(encoding="utf-8")
        write_text(dst, transform(text) if transform else text)
        if str(dst) not in manifest["files"]:
            manifest["files"].append(str(dst))

    agents = sorted((ROOT / "agents").glob("*.md"))
    for a in agents:
        put(a, base / "agents" / a.name)
    tpl = base / "templates" / "workflow.config.md"
    put(ROOT / "templates" / "workflow.config.md", tpl)
    put(ROOT / "skills" / "dev-workflow" / "SKILL.md", base / "skills" / "dev-workflow" / "SKILL.md",
        lambda t: t.replace("${CLAUDE_PLUGIN_ROOT}/templates/workflow.config.md", tpl.as_posix()))
    put(ROOT / "scripts" / "kw_report.py", base / "knowledgewala" / "kw_report.py")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(manifest_path, json.dumps(manifest, indent=2))
    print(f"Installed {len(agents)} agents + /dev-workflow v{manifest['version']} into {base}")
    for name, flag in (("guardrail", with_guardrail), ("observe", with_observe)):
        if flag:
            feature(base, name, True)
        else:
            print(f"{name} not enabled (optional): kw_install.py {name} on")
    print(f"Run report any time: python {base / 'knowledgewala' / 'kw_report.py'}")
    print("Next: restart Claude Code, then run /dev-workflow --status")


def uninstall(base):
    manifest_path = base / "knowledgewala" / "manifest.json"
    if not manifest_path.exists():
        print("Nothing to uninstall (no manifest).")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for f in manifest["files"]:
        p = Path(f)
        if p.exists():
            p.unlink()
    for dst, bak in manifest.get("backups", {}).items():
        if Path(bak).exists():
            shutil.move(bak, dst)
            print(f"  restored your {Path(dst).name}")
    skill_dir = base / "skills" / "dev-workflow"
    if skill_dir.exists() and not any(skill_dir.iterdir()):
        skill_dir.rmdir()
    for name in FEATURES:
        feature(base, name, False)
    manifest_path.unlink()
    try:
        (base / "knowledgewala").rmdir()
    except OSError:
        pass
    print(f"Uninstalled from {base}. Restart Claude Code.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("install", "uninstall", "guardrail", "observe"):
        p = sub.add_parser(name)
        p.add_argument("--scope", choices=("user", "project"), default="user")
        if name == "install":
            p.add_argument("--guardrail", action="store_true")
            p.add_argument("--observe", action="store_true")
        if name in ("guardrail", "observe"):
            p.add_argument("state", choices=("on", "off"))
    a = ap.parse_args()
    base = base_dir(a.scope)
    if a.cmd == "install":
        install(base, a.guardrail, a.observe)
    elif a.cmd == "uninstall":
        uninstall(base)
    else:
        feature(base, a.cmd, a.state == "on")


if __name__ == "__main__":
    sys.exit(main())
