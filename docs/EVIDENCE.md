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

## What it does not show

One small, greenfield, single-language app. Nothing here shows behaviour on a large existing codebase, on other stacks, or at team scale. An independent review of this package (before v1.2.0) found real problems that were then fixed: agent-name namespacing under plugin install, hard-coded connector tool names, an over-eager guardrail, and overstated safety claims. See the CHANGELOG.
