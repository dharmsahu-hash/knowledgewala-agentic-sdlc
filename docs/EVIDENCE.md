# Evidence: one real run

The workflow was used to build **tinyurl-demo**, a small URL shortener (Python standard library, SQLite, one static HTML page). This page records what actually happened, including the shortcuts. Numbers are from that run; one small app is not a benchmark.

## Shape of the run

| | |
|---|---|
| Result | 4 tasks (T1 validation/store, T2 HTTP server, T3 UI, T4 docs), 5 commits, one deploy guide |
| Tests at the end | 127 unit tests + 26 real-browser checks (headless Edge over CDP), all passing |
| Subagent calls | 21 (business-analyst 1, requirement-analyst 1, solution-architect 1, task-planner 1, ai-coding-agent 6, unit-test 2, security 3, performance 2, code-reviewer 2, qa 1, deploy-planner 1) |
| Subagent tokens | about 0.5M in total as reported by the harness (orchestrator context not included) |
| Human gates | satisfied by one instruction ("build this demo end to end"), not by typed `approved:` messages: see deviations |

## What the independent review loop caught

- **Medium security bug** in URL validation: `http://a.com@evil.com` and `http://good.com\@evil.com` were accepted (browsers treat the backslash as `/`, so the redirect lands on a different host than the parser reports). Found by `security-agent` in T1, confirmed by the reviewer, fixed in a second iteration, re-verified by exercising 11 hostile URLs.
- A misleading "slug taken" error for a different constraint failure; PUT/PATCH returning 501 instead of 405; an unbounded list query; a test suite that spent 20 of its 22 seconds waiting on a 0.5 s poll.
- **A wrong suggestion was disproved by measuring.** `performance-agent` estimated that `PRAGMA synchronous=NORMAL` would speed up click counting. The coding agent benchmarked before and after, saw only noise, and reverted it.
- **A tempting change was declined.** The reviewer refused HTTP/1.1 keep-alive because early-return responses would leave unread request bodies and desync the connection.
- The browser check confirmed hostile markup renders as inert text and the 360 px layout does not overflow.

## Honest deviations

- Gates G1/G3 were pre-authorised by the owner's instruction; the orchestrator recorded that and quoted it in each prompt. Nothing technically stops an orchestrator from writing `approved:` itself, so this is a convention.
- `business-analyst` returned `NEEDS_HUMAN_INPUT` with five questions; the orchestrator answered them with documented assumptions to keep the demo moving.
- After the T2 polish pass the three verification agents were not re-run (the reviewer said a glance at the diff sufficed); the orchestrator re-ran the suite and a live smoke test.
- Performance review was skipped for the static page (T3). No Jira issues were created.

## Second run: through the installed plugin (v1.2.0 from GitHub)

To test the packaging, a headless Claude Code session loaded the plugin copy fetched from GitHub (`--plugin-dir`) and ran `/dev-workflow` on a scratch app: **csv2json**, a command-line CSV-to-JSON tool (Python standard library). The operator notice pre-authorised gates G1-G3 for that app and withheld G4, so the run stopped after the deployment guide.

| | |
|---|---|
| Subagent calls | 17 (business-analyst 1, requirement-analyst 1, solution-architect 2, task-planner 1, ai-coding-agent 3, unit-test 2, security 2, performance 1, code-reviewer 1, documentation-generator 1, qa 1, deploy-planner 1) |
| Cost and time | $2.32 as reported by the CLI for the whole session; about 10 minutes |
| Tests | 56 unit tests, **re-run independently afterwards: 56/56 pass**. The qa-agent also reported 39 checks against 10 acceptance criteria (agent-reported, not re-run) |
| Caught by review | a Medium crash (`--delimiter '"'` raised a traceback instead of exit 2), fixed; exit 2 with a clean message was confirmed by hand. One Low (embedded newline broke the one-line stderr format), fixed |
| Checked by hand | file/stdin input, `--pretty`, `--delimiter`, `--output`, and exit codes 3, 4, 5 for a missing file, short row and duplicate header |
| Not shown | POSIX and older Python versions (Windows, Python 3.14 only); no git repo was created because `git init` needed an approval nobody could give |

What this run exposed in the skill, fixed in v1.2.1: the orchestrator batched independent tasks into one review (now allowed only for Low/Medium, independent, disjoint-file tasks, verdict per task); it skipped re-verification after the fix round (now an explicit rule); it accepted an analyst's proposed defaults instead of halting because the run was pre-authorised (now an explicit, bounded exception); and it named the run folder `RUN-001` (now `YYYYMMDD-<slug>`).

## Tool-grant probes (plugin agents ignored `tools` alone)

The second run showed the `business-analyst` (declared `tools: Read, Grep, Glob`) creating a file. A controlled probe asked an agent to write a file, or to list its tools, under different loading modes (Claude Code 2.1.302):

| Test | How the agent was loaded | Result |
|---|---|---|
| A | plugin, headless (`--plugin-dir`), `tools` allowlist only | **file written**; agent listed the full toolset (Write, Edit, Bash, ...) |
| B | project-level agent, interactive session | refused (`NO_WRITE_TOOL`); tools `Read, Grep, Glob` |
| C | project-level agent, headless session | refused; tools `Read, Grep, Glob` |
| D | plugin, headless, allowlist **plus** `disallowedTools` | refused; no file written; tools `Read, Grep, Glob` |

The official docs describe `tools` as an allowlist and do not exempt plugin agents, so test A is either a Claude Code behaviour in this version or specific to `--plugin-dir`; it was not tested with a marketplace-installed plugin under a different login. The mitigation is to deny what an agent must not have, in addition to listing what it has. v1.3.0 does this for the 12 restricted agents and adds a static test (`tests/test_agents.py`).

After the change, all 15 agents were asked for their exact tool names in a plugin-loaded session: **15/15 matched their declared tools**. These lists are self-reported by the agents, so they are strong evidence, not a proof; the file-write probes (A, D) are the direct evidence.

## What it does not show

Two small, greenfield, single-language apps. Nothing here shows behaviour on a large existing codebase, on other stacks, or at team scale. An independent review of this package (before v1.2.0) found real problems that were then fixed: agent-name namespacing under plugin install, hard-coded connector tool names, an over-eager guardrail, and overstated safety claims. See the CHANGELOG.
