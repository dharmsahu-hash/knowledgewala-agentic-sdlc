<div align="center">

# KnowledgeWala &nbsp;|&nbsp; Agentic SDLC for Claude Code

**One command, 15 specialist subagents, human approval gates. From an idea or a Jira ticket to reviewed, tested, documented code, with deployment instructions.**

`MIT` &nbsp;·&nbsp; `v1.2.0` &nbsp;·&nbsp; `Jira optional` &nbsp;·&nbsp; `Windows, macOS, Linux`

*Built by [KnowledgeWala](https://github.com/dharmsahu-hash). If it saves you time, star the repo and tag **@KnowledgeWala**.*

</div>

---

## What it is, and what it is not

`/dev-workflow` runs a small team of focused subagents (analyst, architect, planner, coder, tester, security, performance, reviewer, docs, QA, deploy) so that **the agent that writes the code is never the agent that judges it**. You approve at a few gates; fix loops are capped.

It is **not** a faster way to write code. A multi-agent run costs several times the tokens of one session (see [Cost](#cost-and-speed)). Use it when independent review and a paper trail are worth that.

Evidence from a real run (a small URL shortener built end to end): [`docs/EVIDENCE.md`](docs/EVIDENCE.md). Its review loop caught a Medium security bug, disproved a plausible-but-wrong performance fix by measuring, and produced 127 tests plus a browser check.

## Flow

```
Idea / Jira ticket
  A  ticket-analyst* -> business-analyst -> requirement-analyst    [GATE G1: you approve -> Jira issues]
  B  solution-architect (HLD, LLD)                                  [GATE G2: only for payment/auth/PII/migration]
  C  task-planner                                                   [GATE G3: you type  approved: T1,T2]
  D  per task, max 3 rounds:
       ai-coding-agent -> { unit-test | security | performance } in parallel -> code-reviewer
       BLOCKED -> only the Required Changes list goes back to the coding agent
  E  documentation-generator -> qa-agent (max 2 fix rounds)
  F  deploy-planner (DEPLOY.md: local + production options)         [G4: you type  approved: deploy <app> to local]
     -> deployment-devops-agent (starts it locally, verifies it) -> ops-monitor
     production = plan only; executing it needs its own explicit approval
```
\* only when you start from a ticket. **`--lite`** skips A, B and the Jira write for small changes to an existing repo.

| Agent | Role | Tools | Writes |
|---|---|---|---|
| `ticket-analyst` | Ticket to repo/file mapping and scoped plan | Read, Grep, Glob | nothing |
| `business-analyst` | Idea to goals, users, scope, metrics | Read, Grep, Glob | nothing |
| `requirement-analyst` | Requirements, epics, stories, acceptance criteria | Read, Grep, Glob | nothing |
| `solution-architect` | HLD and LLD (runs on Opus) | Read, Grep, Glob | nothing |
| `task-planner` | Sequenced, estimated tasks and per-task scaffold | Read, Grep, Glob | nothing |
| `ai-coding-agent` | Implements ONE approved task | + Edit, Write, Bash | source |
| `unit-test-agent` | Writes and runs tests | + Edit, Write, Bash | tests |
| `security-agent` | Review, probing, scanners | + Bash | nothing by instruction |
| `performance-agent` | Review and real measurements | + Bash | nothing by instruction |
| `code-reviewer` | One merge verdict and a peer-review doc | + Write | `docs/reviews/` by instruction |
| `documentation-generator` | README, API docs, changelog | + Write | docs by instruction |
| `qa-agent` | Automated tests against the original AC and a manual checklist | + Edit, Write, Bash | tests, `docs/qa/` |
| `deploy-planner` | `docs/deploy/DEPLOY.md`: run locally and ranked production options | + Write | `docs/deploy/` by instruction |
| `deployment-devops-agent` | Runs the local deployment and verifies it; hosted deploys plan-only unless approved | + Bash | gated |
| `ops-monitor` | Post-deploy health and root-cause analysis | + Bash | nothing by instruction |

## Install (pick one)

### A. Claude Code plugin (recommended)

```
/plugin marketplace add dharmsahu-hash/knowledgewala-agentic-sdlc
/plugin install knowledgewala-agentic-sdlc@knowledgewala
```
Restart Claude Code. Plugin components are **namespaced** (verified with `claude --plugin-dir`): the skill is `/knowledgewala-agentic-sdlc:dev-workflow` and agents appear as `knowledgewala-agentic-sdlc:business-analyst` and so on. The skill is written to resolve those names itself. In the examples below, `/dev-workflow` means that namespaced command for plugin installs. Update with `/plugin marketplace update knowledgewala`.

### B. Install script (no plugin system)

Download the zip from the [latest release](https://github.com/dharmsahu-hash/knowledgewala-agentic-sdlc/releases/latest), unzip, then (needs Python 3.8+):

```powershell
.\install\install.ps1                  # your user, all projects      (-Scope project = this folder only)
.\install\install.ps1 -Uninstall       # removes exactly what it installed
```
```bash
./install/install.sh                   # (--project = this folder only)
./install/install.sh --uninstall
```
Your own agents with the same names are backed up (`*.user-backup`) and restored on uninstall.

### C. Manual copy

Copy `agents/*.md` to `~/.claude/agents/` and `skills/dev-workflow/` to `~/.claude/skills/dev-workflow/`. In this mode `${CLAUDE_PLUGIN_ROOT}` in the skill refers to `templates/workflow.config.md`; copy that file to `~/.claude/templates/` and fix the path.

### Optional: destructive-command guardrail (off by default)

A PreToolUse hook that blocks recursive deletes, force-push, `reset --hard`, infra apply/destroy, destructive SQL run through a SQL client, and cloud deletions, in Bash and PowerShell. It ignores quoted text and heredocs, and has a regression suite (`tests/test_guardrail.py`).

```
python install/kw_install.py guardrail on            # --scope project for this folder only
python install/kw_install.py guardrail off
```
It is a **tripwire, not a sandbox**: an interpreter one-liner, alias or encoded payload can get past it, and it fails open on unreadable input. It is opt-in because a global hook should not surprise you.

## First run

```
/dev-workflow "Offline-first flashcard app for school students"
/dev-workflow --lite "Fix the pagination bug in the orders list"
/dev-workflow --ticket PROJ-123      # needs the Atlassian connector
/dev-workflow --resume 20260101-app
```
The first run asks once where to create apps and whether you use Jira, then saves `.claude/workflow.config.md`. Walkthrough: [`docs/EXAMPLE.md`](docs/EXAMPLE.md).

## Cost and speed

Measured on the demo run (4 tasks, tiny app): **21 subagent calls, about 0.5M subagent tokens**. Rule of thumb: about 5 subagent calls per task, up to 15 with three fix rounds, plus about 8 for discovery, design and docs. Each subagent starts cold and re-reads files, which is where multi-agent overhead comes from.

| Use | When |
|---|---|
| `/dev-workflow` full | greenfield app or a feature where review, security and a paper trail matter |
| `/dev-workflow --lite` | one bug or feature in an existing repo (about 3 calls per task) |
| a single agent | "review this diff for security", "plan these tasks", "write the deploy guide" |
| neither | a typo, a config tweak, an exploratory spike: just ask Claude directly |

## What is enforced and what is convention

| | Enforced by | Strength |
|---|---|---|
| Analysts cannot edit files | tool grants (`tools:` has no Write/Edit/Bash) | **hard** |
| Reviewers/security/perf/ops cannot edit files | prompt instruction only (they hold Bash or Write for scanners, measurements, reports) | convention |
| `approved:` before coding or deploying | agent instruction; the orchestrator is the same model that writes the prompt | **convention**, not a lock |
| Only the orchestrator writes to Jira | agents have no Jira tools | **hard** for agents |
| Destructive shell commands | optional guardrail hook | tripwire |
| Loop caps and stagnation stop | skill instructions | convention |

If you need enforced approvals, require a human-created file or a permission prompt for Edit/Write/Bash in your own settings; this package does not pretend to supply that.

## When not to use it

An existing repo with no tests, a tight token budget, quick fixes, or if you need enforced controls rather than conventions. It is also unproven beyond one small Python app so far; treat "works with any stack" as a design goal, not a guarantee.

## Where it fits

Role-based agent packs are common ([wshobson/agents](https://github.com/wshobson/agents), [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)); spec-first flows ([github/spec-kit](https://github.com/github/spec-kit)) and disciplined subagent development ([obra/superpowers](https://github.com/obra/superpowers)) are well established. What this adds: gated Jira round-trip (optional), resumable run state, bounded fix loops with escalation, and a deployment stage (instructions plus an approval-gated local run). Try them side by side.

## Customize

Loop limits, models and Jira defaults: `.claude/workflow.config.md`. Per-agent `model:` / `tools:`: each agent's frontmatter. Skip an agent by removing its file.

## Contributing

Issues and PRs welcome. Keep agents stack-agnostic and the approval gates intact. Run `python -m unittest discover -s tests` and `claude plugin validate .` before a PR.

---

<div align="center"><sub>© KnowledgeWala. MIT licensed; the KnowledgeWala name and logo are not licensed, see <a href="NOTICE.md">NOTICE.md</a>. Not affiliated with Anthropic or Atlassian.</sub></div>
