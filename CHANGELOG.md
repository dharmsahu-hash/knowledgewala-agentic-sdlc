# Changelog

## 1.2.0

Fixes from an independent pre-release review.

- **Plugin install works:** the skill now resolves namespaced agent names (`knowledgewala-agentic-sdlc:business-analyst`); verified with `claude --plugin-dir`.
- **No hard-coded connector tool names:** agents no longer list `mcp__claude_ai_Atlassian_MCP__*`; the orchestrator owns every Jira call and hands ticket text to agents as files.
- **Guardrail rewritten and opt-in:** parses by command position, ignores quoted text and heredocs (no more false positives on commit messages), catches `rm foo -rf`, `rm -r`, `find -delete`, `git push +main`, `git branch -D`, interpreter one-liners; works with `python3 || python`; regression tests added. No longer enabled automatically by the plugin.
- **Installer rewritten** (`install/kw_install.py`): backs up and restores your same-named agents, manifest-based uninstall, never rewrites an unparseable `settings.json`, Python 3.8+. Installer tests added.
- **New `--lite` mode** for small changes, and a cost estimate printed before gate G3.
- **Honest docs:** README states what is enforced vs convention, real cost numbers, when not to use it; `docs/EVIDENCE.md` records a real run including deviations.
- Agent descriptions no longer say "use PROACTIVELY" so they do not auto-fire outside the workflow.

## 1.1.0

- New agent `deploy-planner`: writes `docs/deploy/DEPLOY.md` with local run steps and ranked production options for the detected stack (docs only, deploys nothing).
- `deployment-devops-agent` gains a **local target**: after `approved: deploy <app> to local` it starts the app on 127.0.0.1, verifies it with a real request, and reports URL, PID and stop command. Hosted deployments stay plan-only unless explicitly approved.
- `dev-workflow` Phase F rewritten with gate G4 (local deployment approval).
- Now 15 agents.

## 1.0.0

- First public release: `/dev-workflow` skill and 14 subagents (ticket-analyst, business-analyst, requirement-analyst, solution-architect, task-planner, ai-coding-agent, unit-test-agent, security-agent, performance-agent, code-reviewer, documentation-generator, qa-agent, deployment-devops-agent, ops-monitor).
- Approval gates, bounded fix loops with stagnation detection, resumable run state in `.workflow/`.
- Optional Jira integration through the Atlassian connector.
- Guardrail PreToolUse hook for destructive shell commands (Bash and PowerShell).
- Install as a Claude Code plugin or with `install.ps1` / `install.sh`.
