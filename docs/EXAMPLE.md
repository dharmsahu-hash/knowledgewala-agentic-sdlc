# Worked example: from idea to reviewed code

An illustrative session. Your actual agent output will differ; the shape, gates and commands are what to expect.

## 0. Install and check

```
/plugin marketplace add dharmsahu-hash/knowledgewala-agentic-sdlc
/plugin install knowledgewala-agentic-sdlc@knowledgewala
```
Restart Claude Code, open (or create) a folder for your work, and run:

```
/dev-workflow --status
```
Expected: "no runs found". That confirms the skill loaded.

## 1. Start with an idea

```
/dev-workflow "Offline-first flashcard web app for school students, with spaced repetition"
```

**First run only**, you are asked once:

```
1. Where should new apps be created?              -> C:\Users\you\repos
2. Do you use Jira? (site URL + project key)      -> no   (or: https://acme.atlassian.net, key APP)
3. Keep default loop limits (3 build / 2 QA)?     -> yes
```
Answers are saved to `.claude/workflow.config.md`.

## 2. Phase A: requirements (gate G1)

`business-analyst` and `requirement-analyst` run. You get a short status line, then the gate:

```
G1: Requirements ready (run 20260101-flashcards)
  Epic  [EPIC] Study sessions with spaced repetition
   Story [STORY] Review due cards         AC: Given cards are due, When I open a session, Then I see only due cards
   Story [STORY] Work offline             AC: Given no network, When I review, Then progress is saved and synced later
  Flagged: none (no payment/auth/PII)
Approve to create these in Jira / continue?
```
Reply `approve`, or edit: `drop the sync story, add CSV import`. With Jira connected, issues are created now, not before.

## 3. Phase B and C: design and plan (gate G3)

`solution-architect` writes the HLD and LLD, `task-planner` splits the work:

```
G3: 4 tasks
  T1 Project scaffold + build/test scripts        Low     2-3h  [Medium confidence]
  T2 Card model + scheduling algorithm            Medium  3-5h
  T3 Offline storage layer                        Medium  3-4h
  T4 Review UI                                    Low     4-6h
```
Approve the tasks you want built, naming each ID:

```
approved: T1, T2
```
Not approval: "yes", "go ahead", "sounds good".

## 4. Phase D: the build loop (per task)

For T2 the orchestrator runs:

```
ai-coding-agent        implements T2 only
unit-test-agent  \
security-agent    >-- run in parallel
performance-agent/     (skipped for tasks with no data/API code, and the skip is recorded)
code-reviewer          verdict
```

Round 1 verdict, for example:
```
BLOCKED
 R1  src/schedule.ts:41  interval overflows after 30 reviews  (unit-test-agent)  -> clamp to max interval
 R2  src/schedule.ts:58  Date.now() used directly, untestable (code-reviewer)    -> inject a clock
```
Only R1 and R2 go back to the coding agent. Round 2 verdict: `APPROVED WITH FOLLOW-UPS`, with one Low finding logged as a follow-up. The loop exits.

If the same finding survives two rounds, or round 3 is still blocked, the run stops and asks you:
```
STOPPED: R1 unresolved after 2 rounds (stagnation). Options: relax the AC, approve a wider scope, or take over by hand.
```

## 5. Phase E: docs and QA

`documentation-generator` updates the README and changelog from the real code. `qa-agent` builds tests against the original acceptance criteria and writes `docs/qa/<feature>-qa-steps.md` for a human tester.

## 6. Resume any time

Close Claude Code whenever you like. Later:

```
/dev-workflow --resume 20260101-flashcards
```
State lives in `<app>/.workflow/20260101-flashcards/state.json` plus one artifact per stage.

## 7. Start from a Jira ticket instead

```
/dev-workflow --ticket APP-42
```
`ticket-analyst` reads the ticket (read-only), maps it to files, flags risks, and the run continues at requirements.

## 8. Deploy: instructions first, local run on approval

After QA passes, `deploy-planner` writes `docs/deploy/DEPLOY.md` for the detected stack and the orchestrator asks:

```
G4: DEPLOY.md written (local run + production options: <primary>, <cheapest>, <alternative>)
Local command:  python -m tinyurl        Verify: GET http://127.0.0.1:8000/api/links -> 200
Deploy locally now? Reply `approved: deploy <app> to local`
```
Reply:
```
approved: deploy tinyurl-demo to local
```
`deployment-devops-agent` then starts it on 127.0.0.1, checks it with a real request, and reports the URL, the PID and how to stop it. Without that line nothing is started.

Production is plan-only: execution needs its own `approved: deploy <app> to <env>`, and pushes, remote repos and paid accounts remain your decision. Afterwards ask `ops-monitor` to check health.

## Using one agent on its own

Every agent also works without the orchestrator:

```
Use security-agent to review the changes in src/auth.ts
Use solution-architect in LLD mode on <paste or file path>
```
