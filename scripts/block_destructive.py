#!/usr/bin/env python3
"""PreToolUse guardrail: a tripwire for obviously destructive shell commands.

Reads the Claude Code tool-call JSON on stdin; exit 2 (reason on stderr) blocks.

What it is: a best-effort filter that parses commands by position. Quoted
strings and heredoc bodies are ignored, so `git commit -m "delete from x"` is fine.
What it is NOT: a sandbox. Anything run through an interpreter, an alias or an
encoded payload can get past it, and it fails OPEN on unreadable input.
It does not replace Claude Code's own permission prompts.
"""
import json
import re
import sys

SQL_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "sqlcmd", "mongosh", "duckdb", "clickhouse-client"}
PREFIXES = {"sudo", "env", "command", "time", "nohup", "nice", "exec"}
RM_LIKE = {"rm", "rmdir", "del", "erase", "rd", "ri", "remove-item"}


def strip_quotes(cmd: str) -> str:
    cmd = re.sub(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?:\n|$)", "\n", cmd, flags=re.S)
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"(?:\\.|[^"\\])*"', '""', cmd)
    return cmd


def segments(bare: str):
    for seg in re.split(r"\|\||&&|;|\||\n", bare):
        toks = seg.split()
        while toks and (toks[0].lower() in PREFIXES or re.fullmatch(r"\w+=\S*", toks[0])):
            toks = toks[1:]
        if toks:
            yield toks


def recursive_flag(tokens) -> bool:
    for t in tokens:
        low = t.lower()
        if low in ("--recursive", "-recurse", "/s"):
            return True
        if re.fullmatch(r"-[a-zA-Z]+", t) and "r" in low:
            return True
    return False


def check(cmd: str):
    """Return a reason string if the command should be blocked, else None."""
    bare = strip_quotes(cmd)
    for toks in segments(bare):
        head = toks[0].lower().rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        head = re.sub(r"\.exe$", "", head)
        rest = toks[1:]
        low = [t.lower() for t in rest]

        if head in RM_LIKE and recursive_flag(rest):
            return "recursive delete"
        if head == "find" and ("-delete" in low or ("-exec" in low and "rm" in low)):
            return "find -delete / -exec rm"
        if head in ("terraform", "tofu") and low[:1] and low[0] in ("apply", "destroy"):
            return "infrastructure apply/destroy"
        if head == "kubectl" and low[:1] and low[0] in ("delete", "apply") and not any(t.startswith("--dry-run") for t in low):
            return "kubectl delete/apply"
        if head in ("aws", "gcloud", "az") and any(t in ("rm", "delete") or t.startswith(("delete-", "terminate")) for t in low):
            return "cloud resource deletion"
        if head == "git" and low:
            sub = next((t for t in low if not t.startswith("-")), "")
            if sub == "push" and any(t == "-f" or t.startswith("--force") or (t.startswith("+") and len(t) > 1) for t in low):
                return "force push"
            if sub == "reset" and "--hard" in low:
                return "git reset --hard"
            if sub == "clean" and any(re.fullmatch(r"-[a-z]*f[a-z]*", t) for t in low):
                return "git clean -f"
            if sub == "branch" and "-D" in rest:
                return "git branch -D"
            if sub == "checkout" and "--" in rest and "." in rest:
                return "git checkout -- . (discards changes)"
        if head.startswith("mkfs") or head == "format" or (head == "dd" and any(t.startswith("if=") for t in low)):
            return "disk format/overwrite"
        if head.startswith(("python", "py", "node")) and ("-c" in low or "-e" in low):
            if re.search(r"rmtree|os\.remove|os\.unlink|unlink\(|rmSync|\brm\(", cmd):
                return "interpreter one-liner that deletes files"
        if head in SQL_CLIENTS and re.search(r"\b(drop|truncate)\s+(table|database|schema)\b|\bdelete\s+from\b", cmd, re.I):
            return "destructive SQL"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
        cmd = (data.get("tool_input") or {}).get("command", "")
        if not isinstance(cmd, str):
            return 0
        reason = check(cmd)
    except Exception:
        return 0  # fail open by design
    if reason:
        sys.stderr.write(f"Blocked by the KnowledgeWala guardrail: {reason}. "
                         "Ask the owner to run this themselves if it is truly intended.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
