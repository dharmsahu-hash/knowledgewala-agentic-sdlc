#!/usr/bin/env bash
# KnowledgeWala Agentic SDLC installer (macOS / Linux / Git Bash). Thin wrapper over kw_install.py (needs Python 3).
#   ./install/install.sh                  install for your user (all projects)
#   ./install/install.sh --project        install into ./.claude of the current folder
#   ./install/install.sh --guardrail      also enable the optional destructive-command hook
#   ./install/install.sh --uninstall      remove exactly what was installed, restore your backups
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "Python 3 is required to run the installer. Or copy agents/ and skills/ by hand (README, Option C)."; exit 1; }
SCOPE=user; CMD=install; EXTRA=()
for a in "$@"; do
  case "$a" in
    --project) SCOPE=project ;;
    --uninstall) CMD=uninstall ;;
    --guardrail) EXTRA+=(--guardrail) ;;
    --observe) EXTRA+=(--observe) ;;
    *) echo "unknown option: $a"; exit 1 ;;
  esac
done
exec "$PY" "$HERE/kw_install.py" "$CMD" --scope "$SCOPE" ${EXTRA[@]+"${EXTRA[@]}"}
