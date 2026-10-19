# Releasing (maintainer runbook)

Nothing here runs automatically. Each step that publishes (push, release) is yours to run.

## One-time: create the GitHub repo

Pick the owner and visibility first (`dharmsahu-hash` is assumed below; change it if you use an org). The plugin install commands in the README use the same `owner/repo`, so if you rename, search and replace `dharmsahu-hash` across the repo.

```powershell
cd <path-to>\knowledgewala-agentic-sdlc
gh auth status                                   # must be logged in
git init -b main
git add -A
git commit -m "KnowledgeWala Agentic SDLC v1.3.0"
gh repo create dharmsahu-hash/knowledgewala-agentic-sdlc --public --source . --push `
  --description "KnowledgeWala Agentic SDLC: /dev-workflow + 15 Claude Code subagents"
gh repo edit --add-topic claude-code --add-topic ai-agents --add-topic sdlc --add-topic jira --add-topic knowledgewala
```

## Each release

1. Bump the version in **three** places: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and the watermark line in `agents/*.md` and `skills/dev-workflow/SKILL.md`. Add a `CHANGELOG.md` entry.
2. Validate and build:

```powershell
claude plugin validate .
.\scripts\build-release.ps1 -Version 1.3.0      # writes dist\knowledgewala-agentic-sdlc-v1.3.0.zip + .sha256
```
3. Tag and publish the release with the zip attached:

```powershell
git add -A; git commit -m "Release v1.3.0"
git tag v1.3.0
git push origin main --tags
gh release create v1.3.0 `
  dist\knowledgewala-agentic-sdlc-v1.3.0.zip dist\knowledgewala-agentic-sdlc-v1.3.0.zip.sha256 `
  --title "KnowledgeWala Agentic SDLC v1.3.0" --notes-file CHANGELOG.md
```

## Verify like a user

In a clean Claude Code install (or another machine):

```
/plugin marketplace add dharmsahu-hash/knowledgewala-agentic-sdlc
/plugin install knowledgewala-agentic-sdlc@knowledgewala
/dev-workflow --status
```
Also test the zip path: unzip, run `install\install.ps1 -Scope project` in an empty folder, restart, run `/dev-workflow --status`.

## Checklist before going public

- [ ] No personal data: `git grep -n -i -E "atlassian.net|cloudId|C:\\\\Users|D:\\\\"` finds nothing unexpected
- [ ] `LICENSE` is the license you want (MIT assumed)
- [ ] README handle and links point to the real repo
- [ ] Logo added to the README header (optional)
- [ ] Short demo video attached to the README or release (see `media/`)
