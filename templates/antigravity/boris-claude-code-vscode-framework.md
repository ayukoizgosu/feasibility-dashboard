---
title: "Boris Cherny-style Claude Code + VS Code Operating System"
tags: [claude-code, vscode, workflows, agents, antigravity-ingest]
created: 2026-01-10
---

## What this document is
A **repeatable, repo-shareable framework** for using **Claude Code** (CLI + VS Code extension) with **high throughput and high correctness**, inspired by **Boris Cherny’s “how I use Claude Code” workflow** and aligned with **official Claude Code + VS Code docs**.

---

## Core principles (Boris-style)
1. **Parallelism is the default**
   - Treat Claude sessions as a *work queue*: multiple sessions in parallel, each with a single purpose (tests, refactor, docs, bugfix, etc.).
2. **Plan → approve → execute**
   - For anything non-trivial: **start in Plan Mode**, iterate on the plan, then switch to **auto-accept** for a one-shot execution run.
3. **Repo memory beats re-prompting**
   - Maintain a **shared `CLAUDE.md`** and update it whenever Claude repeats a mistake.
4. **Automate the inner loop**
   - Encode repeated workflows as **slash commands** and/or **subagents** so the workflow is callable *by you and by Claude*.
5. **Automate the last 10%**
   - Use **hooks** for formatting / linting / deterministic verification steps so CI failures don’t happen “later”.
6. **Never code without a verification loop**
   - Give Claude a **reliable, deterministic way to verify** changes (tests, lint, UI script, simulator, etc.). This is the biggest multiplier.

---

## Minimal repo scaffold (copy/paste mental model)
```
repo/
  CLAUDE.md
  .claude/
    commands/
      commit-push-pr.md
      test.md
      lint-fix.md
      repro.md
    agents/
      code-simplifier.md
      verify-app.md
    settings.json
    hooks/                 # if you store scripts here
  .mcp.json                # if you share MCP tools in-repo
  .vscode/
    tasks.json
    launch.json
```

---

## 1) Throughput architecture: “5× local + N× web” queue
### Operating model
- Maintain **multiple Claude sessions**:
  - **Local**: run `claude` in several terminal tabs (each tab = one task).
  - **Web**: run multiple `claude.ai/code` sessions for long-running or async work; hand off/teleport sessions as needed.
- Use **system notifications** so you don’t context-switch constantly.

### Practical guardrails
- One task per session (avoid mixing refactor + bugfix + docs).
- Name sessions by deliverable (e.g., `AUTH-REFAC`, `E2E-FLAKE`, `DOCS`).

---

## 2) Default workflow: Plan → Auto-accept execution
### The “Boris loop”
1. **Start in Plan Mode** (Shift+Tab twice).
2. Ask for:
   - **file-level impact list**
   - **implementation steps**
   - **verification steps (mandatory)**
   - **rollback strategy** (git / checkpoints)
3. Iterate until the plan is good.
4. Switch to **auto-accept edits** and run execution.

### Plan prompt template
- “Create a plan to implement X. The plan must include: impacted files, step-by-step edits, and a verification checklist with commands.”

---

## 2.5) Superpowers integration (optional)
Superpowers can drive the Plan -> Execute loop with structured skills.
- /superpowers:brainstorm -> design doc in docs/decisions or ARCHITECTURE.md
- /superpowers:write-plan -> file-level plan with tests and rollback
- /superpowers:execute-plan -> batch execution with verification checkpoints
Keep local guardrails: small diffs, verification required, update CLAUDE.md.

## 3) Team memory: `CLAUDE.md` as “policy + landmines”
### What to put in `CLAUDE.md`
- **Local conventions**: architecture rules, naming, lint rules, folder boundaries, testing philosophy.
- **Known footguns**: “don’t touch X”, “always do Y before Z”, “when editing foo, update bar”.
- **Build/test commands** and expected output.
- **Style preferences**: e.g., “small diffs”, “avoid cleverness”, “prefer explicit errors”.

### Rule
Whenever Claude does something wrong **twice**, it becomes a `CLAUDE.md` line item.

---

## 4) Inner-loop automation with slash commands
### When to create a slash command
- If you type the same prompt **>3×/day**, convert it into a command.
- If the command benefits from **precomputed context** (git status, grep results), embed bash to reduce back-and-forth.

### Slash command pattern
- **Inputs**: `$ARGUMENTS` (or explicit placeholders)
- **Precompute**: gather minimal state (git diff/status, failing tests, logs)
- **Action**: instruct Claude with deterministic steps

#### Example: `/commit-push-pr`
Create `.claude/commands/commit-push-pr.md`:
```md
Commit, push, and open a PR.

Context (run first):
! git status
! git diff --stat

Steps:
1) Propose a concise commit message based on diff.
2) Commit and push to current branch.
3) Draft a PR title + description (include “What/Why/How/Testing”).
4) Output the PR URL (or the exact command to open it).
```

---

## 5) Subagents: “specialists” you can invoke or let Claude delegate to
### Use cases
- **code-simplifier**: “post-pass” to simplify or normalize code after feature work.
- **verify-app**: consistent end-to-end validation checklist.
- **security-reviewer**, **perf-reviewer**, **db-migration-reviewer**, etc.

- **bug-triage**: turn reports into deterministic repro steps and a failing test.
- **docs-updater**: keep README/changelog in sync with user-facing changes.
- **release-checker**: verify versioning, changelog, and readiness.

### Subagent design rules
- Narrow scope.
- Deterministic outputs (checklists, diffs, commands).
- Minimal tools (principle of least privilege).

#### Subagent template
Create `.claude/agents/verify-app.md`:
```md
---
name: verify-app
description: Run the full verification suite and fix failures.
tools: [bash, files]
---

You are a verification agent. Your job:
1) Run the verification commands in order.
2) If something fails, locate root cause, propose minimal fix, apply it.
3) Repeat until green. Then summarize what changed and why.
```

---

## 6) Hooks: automate formatting + deterministic checks
### The “last 10%” hook
- Format after tool use, so CI doesn’t fail later.

#### Example: PostToolUse formatter hook (concept)
- Trigger on file edits.
- Run: formatter/linter (e.g., `prettier`, `ruff format`, `gofmt`).
- Optional: stage formatted changes automatically (if your workflow allows).

---

## 7) Permissions: avoid `--dangerously-skip-permissions` for daily work
### Default
- Prefer `/permissions` + shared `.claude/settings.json` allowlist for safe commands.
- Use “don’t ask” or skip-permissions **only in sandbox** for long autonomous runs.

---

## 8) Tools via MCP: make Claude a first-class operator
### High leverage tools (examples)
- Slack search/posting
- Analytics (BigQuery / SQL)
- Error triage (Sentry logs)
- Repo automation (CI status, PR comments)

### Rule
Share MCP config in-repo (`.mcp.json`) so the team has consistent capabilities.

---

## 9) Verification: the non-negotiable multiplier
### Verification ladder (pick the strongest you can)
1. **Unit tests**
2. **Integration tests**
3. **End-to-end UI script**
4. **Manual reproducible steps**
5. **Static analysis / lint / typecheck**

### Prompt enforcement
- Every plan must include a **verification section** with explicit commands.

### Anti-patterns
- “Looks good” without execution.
- “Should work” without a reproducible path.
- “Fixed” without rerunning tests.

---

## 9.5) Usage logging: track tokens and cost
- Log model, input tokens, output tokens, and estimated cost after each session.
- Keep logs in `.claude/logs/usage.jsonl` via `scripts/log-usage.ps1`.
- Update `.claude/usage-rates.json` with per-1k prices for your models.

---

## 10) VS Code: use the extension for review + context, CLI for power
### Extension strengths
- Inline diffs + explicit permission prompts
- @-mention **file + line ranges** from a selection (fast grounding)
- Multiple conversations in tabs/windows
- Switchable “terminal mode” inside VS Code

### CLI strengths
- Full slash commands
- MCP configuration
- Bash shortcuts (`! ...`)
- Some advanced features arrive in CLI first

---

## 11) VS Code workflow upgrades that make Claude better
### A) Use Tasks as deterministic “verification primitives”
- Create `tasks.json` entries for:
  - `test:unit`
  - `test:integration`
  - `lint`
  - `typecheck`
  - `e2e`
- Claude can run these through terminal, but you get a **single canonical definition** per repo.

### B) Debugger as “ground truth”
- Maintain `launch.json` so any bugfix can be verified under a debugger.
- Ask Claude to:
  - add a debug config if missing
  - reproduce under F5
  - capture stack trace + fix + rerun

### C) Source Control UI for fast review discipline
- Always review diffs before commit.
- Stage in small chunks.
- Use branch naming conventions for parallel Claude work.

---

## 12) “Boris OS” daily routine (copyable)
### Morning (10 min)
- Start 3–5 sessions:
  1) **Backlog triage** in Plan Mode (produce plans only)
  2) **Test flake fixer**
  3) **Refactor debt** (bounded)
  4) **Docs / changelog**
- Add any new “Claude mistake patterns” to `CLAUDE.md`.

### During the day
- For each task: Plan → approve → auto-accept execution → verify → PR.
- Convert repeated prompts into slash commands.
- Add verification to anything missing it.

### End of day (5 min)
- Merge `CLAUDE.md` improvements.
- Promote useful ad-hoc prompts → commands/agents.

---

## 13) Ready-to-use checklists
### PR checklist
- [ ] Plan agreed (files + steps + verification)
- [ ] Changes are minimal and localized
- [ ] Formatting hook ran / format clean
- [ ] Tests + lint + typecheck green
- [ ] PR description includes: What/Why/How/Testing

### `CLAUDE.md` hygiene checklist
- [ ] Build/test commands documented
- [ ] Known footguns listed
- [ ] “Do not do” rules are explicit
- [ ] Updated when mistakes repeat

---

## Sources (URLs kept in a code block for ingest hygiene)
```text
Boris thread mirror (ThreadReader): https://threadreaderapp.com/thread/2007179832300581177.html
Claude Code Docs — Terminal config: https://code.claude.com/docs/en/terminal-config
Claude Code Docs — Common workflows (Plan Mode, subagents, etc.): https://code.claude.com/docs/en/common-workflows
Claude Code Docs — VS Code extension usage: https://code.claude.com/docs/en/vs-code
Claude Code Docs — Interactive mode: https://code.claude.com/docs/en/interactive-mode
Claude Code Docs — Settings: https://code.claude.com/docs/en/settings
Anthropic news (VS Code extension, checkpoints): https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously
VS Code Docs — Terminal basics: https://code.visualstudio.com/docs/terminal/basics
VS Code Docs — Tasks: https://code.visualstudio.com/docs/debugtest/tasks
VS Code Docs — Debug config: https://code.visualstudio.com/docs/debugtest/debugging-configuration
VS Code Docs — Source control overview: https://code.visualstudio.com/docs/sourcecontrol/overview
```
