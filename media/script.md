# Social media kit

| File | Use |
|---|---|
| `knowledgewala-agentic-sdlc.mp4` | 1080x1920 vertical video, about 93 s, narrated with the Windows built-in voice. Reels, Shorts, LinkedIn, X. |
| `social-card.png` | 1200x630 link-preview card (GitHub social preview, LinkedIn, X). |
| `build-video.ps1` | Rebuilds the video from `video.html` (needs Edge, ffmpeg; Windows). Edit the narration in the `$lines` array and the scenes in `video.html`. |

Tip: the built-in voice is functional but robotic. For a more natural result, record your own voice over the video or replace the `.wav` step with your preferred text-to-speech tool.

## Narration (matches the video)

1. What if the AI that writes your code is never the one that checks it?
2. One big prompt gives you code with no independent review. KnowledgeWala's workflow splits the job across fifteen focused agents for Claude Code, with human approval gates.
3. Type slash dev-workflow with an idea or a Jira ticket. It plans, then pauses for your approval before any code is written. Then a capped loop: code, test, security, performance, and review.
4. We used it to build a real URL shortener. The loop caught a security bug where a link like `a.com@evil.com` would be accepted and redirect to the wrong host. The result: 127 tests and 26 browser checks, all passing.
5. Now the honest part. That four-task app took 21 subagent calls and about half a million tokens. For small changes, use lite mode. One suggested performance fix was benchmarked, showed no gain, and was reverted.
6. When QA passes, a deploy planner writes your local and production instructions. A local deployment only starts when you type: approved, deploy, to local.
7. It is open source and MIT licensed. Install it as a Claude Code plugin from KnowledgeWala on GitHub.

Every number above is from the recorded run in `docs/EVIDENCE.md`.

## Post text

Build with an AI dev team where the agent that writes the code is never the one that reviews it. 15 Claude Code subagents, human approval gates, capped fix loops, optional Jira. Real run: caught a security bug, 127 tests + 26 browser checks. Honest cost: 21 subagent calls, about 0.5M tokens for a 4-task app; `--lite` for small changes. Open source, MIT.

#KnowledgeWala #ClaudeCode #AIAgents #AgenticAI #SoftwareEngineering #DevTools

## Before you post

- Publish the GitHub repo first: the video and card show `dharmsahu-hash/knowledgewala-agentic-sdlc` and the install command only works once it exists.
- Replace the handle in the post text with your real social handle.
