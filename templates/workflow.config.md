# Workflow configuration

Read by the `dev-workflow` skill and by the agents. Edit values here, not in the agent files.
Copy of this template lives at `.claude/workflow.config.md` in your project.

## Jira (optional)

- site: <https://YOUR-SITE.atlassian.net>   <!-- leave blank to run without Jira -->
- cloudId: <resolved automatically on first run>
- project_key: ASK   <!-- set a key (e.g. APP) or leave ASK to be asked once per run -->
- issue_types: discover the project's real types first. If only Task exists, create `[EPIC] ...` / `[STORY] ...` / `[DEFECT] ...` titled Tasks.
- writes: only the orchestrator writes to Jira, and only after the human approves the requirements (gate G1). Agents never write to Jira.

## Code repositories

- repos_root: <ABSOLUTE PATH, e.g. C:\Users\you\repos or /home/you/repos>
- new_app_dir: `<repos_root>/<app-slug>` (kebab-case slug derived from the idea; confirmed at G1)
- vcs: local git only. Never push, merge, deploy or create a remote repo unless the owner asks in the current session.

## Run state

- run_dir: `<app_dir>/.workflow/<RUN-ID>/` (RUN-ID = `YYYYMMDD-<slug>`); add `.workflow/` to the app's `.gitignore`
- files: `state.json` plus one artifact per stage (`01-business.md`, `02-requirements.md`, `03-hld.md`, `04-lld.md`, `05-tasks.md`, `build/<TASK-ID>/...`)

## Loop limits

- build_fix_iterations_max: 3 per task
- qa_fix_iterations_max: 2
- stagnation_rule: if the same finding (same file and rule) survives 2 consecutive iterations, stop and escalate to the human
- handoff_max_words: 400 (agents pass file paths to artifacts, never pasted contents)

## Models

- default: sonnet
- solution-architect: opus
- change per agent in its frontmatter `model:` field
