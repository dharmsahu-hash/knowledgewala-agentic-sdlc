# Changelog

## Unreleased (1.3.0)

Logs and observability.

- **`scripts/kw_report.py`:** builds `run-report.md` and `run-timeline.log` in the run folder from Claude Code's own transcripts: per-subagent timing, turns, tools, tokens, files written, statuses, permission denials (with kind and agent), approval-text check, parallelism, shell commands. Zero setup.
- **`scripts/kw_trace.py` + `kw_install.py observe on|off`:** opt-in live logger writing `run.log` and `events.jsonl` into the run folder. Verified against real hook payloads. Never prints, never reads results, masks secrets, no-op outside workflows, refuses to create folders for a non-existent cwd.
- Installer now manages both optional hooks (`guardrail`, `observe`), installs `kw_report.py`, and uninstall removes both.
- Skill: `state.json` carries a `history` array (one entry per stage) and the closing report points to the report command.
- **Tool-grant fix:** a plugin-loaded `business-analyst` (declared `Read, Grep, Glob`) was observed creating a file; the same agent as a project-level agent was correctly restricted. Adding `disallowedTools` made the plugin agent refuse. All restricted agents now carry both lists, with a static test (`tests/test_agents.py`). A live probe of all 15 agents was not completed (usage limit).
- Tests: 26 (was 10).

## 1.2.1

Skill fixes from a full end-to-end test through the installed plugin (see `docs/EVIDENCE.md`, second run).

- **Batching rule:** independent Low/Medium tasks with disjoint files may be coded in parallel and share one verification round and one reviewer call (a verdict per task is required). High/Critical tasks and tasks sharing files run alone.
- **After a fix round:** unit tests always re-run; security/performance only if they had open findings or the fix touched their area; the reviewer re-runs after a `BLOCKED` verdict. Fix-now polish after `APPROVED WITH FOLLOW-UPS` is verified by the orchestrator against the diff and says so.
- **Unattended runs:** explicit, bounded exception to "halt on NEEDS_HUMAN_INPUT" when the human has pre-authorised the run and said not to ask questions: accept the analyst's proposed defaults, record them as assumptions, list them in the closing report. Blocked, Critical, payment/auth/PII/migration, missing agents, credentials and unnamed gates still stop the run.
- **Run folder name** is `YYYYMMDD-<app-slug>`, never `RUN-001`.
- **Closing report** is now required: stages, calls per agent, findings, real test counts, accepted assumptions and every deviation from the skill.
- Build script writes the `.sha256` file with LF line endings (CRLF broke `sha256sum -c` on macOS/Linux).

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
