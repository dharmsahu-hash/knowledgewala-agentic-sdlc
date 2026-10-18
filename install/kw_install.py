#!/usr/bin/env python3
"""KnowledgeWala Agentic SDLC installer (no plugin system needed).

  kw_install.py install   [--scope user|project] [--guardrail]
  kw_install.py uninstall [--scope user|project]
  kw_install.py guardrail on|off [--scope user|project]

user scope    -> ~/.claude        (all projects)
project scope -> ./.claude        (current folder only)

Safe by design: existing agents with the same name are backed up (*.user-backup)
and restored on uninstall; a manifest records exactly what was installed; a
settings.json that cannot be parsed is never modified (you get a snippet to
paste instead); the guardrail hook is OFF unless you ask for it.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = "KnowledgeWala Agentic SDLC"
HOOK_ID = "block_destructive.py"


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


def snippet(script):
    return json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell",
                      "hooks": [{"type": "command", "command": hook_command(script)}]}]}}, indent=2)


def edit_settings(base, script, add):
    path = base / "settings.json"
    try:
        data = load_settings(path)
    except Exception as e:
        print(f"! Could not parse {path} ({e}).\n  Not modified. To enable the guardrail add this yourself:\n{snippet(script)}")
        return False
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    ours = lambda e: any(HOOK_ID in h.get("command", "") for h in e.get("hooks", []))
    if add:
        if any(ours(e) for e in pre):
            print("guardrail already enabled")
            return True
        pre.append(json.loads(snippet(script))["hooks"]["PreToolUse"][0])
    else:
        hooks["PreToolUse"] = [e for e in pre if not ours(e)]
        if not hooks["PreToolUse"]:
            del hooks["PreToolUse"]
        if not hooks:
            del data["hooks"]
    if path.exists() and not (base / "settings.json.kw-backup").exists():
        shutil.copy2(path, base / "settings.json.kw-backup")
    base.mkdir(parents=True, exist_ok=True)
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def guardrail(base, on):
    kw = base / "knowledgewala"
    script = kw / HOOK_ID
    if on:
        kw.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts" / HOOK_ID, script)
        if edit_settings(base, script, True):
            print(f"guardrail ON ({script}). Restart Claude Code.")
    else:
        edit_settings(base, script, False)
        if script.exists():
            script.unlink()
        print("guardrail OFF")


def install(base, with_guardrail):
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

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Installed {len(agents)} agents + /dev-workflow v{manifest['version']} into {base}")
    if with_guardrail:
        guardrail(base, True)
    else:
        print("Guardrail hook not enabled (optional): kw_install.py guardrail on")
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
    guardrail(base, False)
    manifest_path.unlink()
    try:
        (base / "knowledgewala").rmdir()
    except OSError:
        pass
    print(f"Uninstalled from {base}. Restart Claude Code.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("install", "uninstall", "guardrail"):
        p = sub.add_parser(name)
        p.add_argument("--scope", choices=("user", "project"), default="user")
        if name == "install":
            p.add_argument("--guardrail", action="store_true")
        if name == "guardrail":
            p.add_argument("state", choices=("on", "off"))
    a = ap.parse_args()
    base = base_dir(a.scope)
    if a.cmd == "install":
        install(base, a.guardrail)
    elif a.cmd == "uninstall":
        uninstall(base)
    else:
        guardrail(base, a.state == "on")


if __name__ == "__main__":
    sys.exit(main())
