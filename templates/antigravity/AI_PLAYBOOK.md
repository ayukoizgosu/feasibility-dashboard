
# AI Playbook (Antigravity Vibe Coding)

This repo is built with heavy AI assistance. These rules make that safe, fast, and cheap.

## Goals
- Ship **small-business-grade** software: secure-by-default, low-ops, low-cost.
- Keep changes **small, reversible, test-backed**.

## Non‑negotiables (ship gate)
1. **Access control**: server-side, **deny-by-default**, centralized, consistent object-level checks.
2. **No secrets** in repo, logs, screenshots, or client bundles.
3. **Every change** includes: tests (incl. negative security tests), lint/format, and rollback.
4. **Minimal diffs**: aim ≤200 LOC per PR; feature flag risky changes.
5. **Dependency discipline**: pin versions; generate SBOM on release/CI.

## How we use AI (applies to Antigravity agents, ChatGPT Projects, Gemini Gems, Perplexity)
### Standard response format for AI assistants
- Assumptions (explicit)
- Patch plan (ordered, small diffs)
- Diffs (unified diff per file)
- Tests (new/updated)
- Commands (copy/paste)
- Risks remaining + mitigations
- Rollback plan

### Prompt macros
**Macro: Small-App Blueprint**
- components + data flows + trust boundaries
- assumptions/constraints (traffic, sensitivity, latency, budget)
- decisions (security/reliability/cost/ops/perf)
- threat list + mitigations
- rollout + rollback
- cost drivers + caps

**Macro: Security hardening pass**
- enumerate endpoints/jobs/schedules
- map authN + authZ
- IDOR/priv-esc sweep
- injection sweep
- secret sweep
- add tests + CI gates

## Repo-first protocol (AI must do this)
AI reads these files first; if missing, create stubs before coding:
- README.md
- ARCHITECTURE.md
- AUTH_MODEL.md
- SECURITY_CHECKLIST.md
- THREAT_MODEL.md
- SLO.md
- OBSERVABILITY.md
- SUPERPOWERS.md (if using superpowers workflow)
- RESOURCES.md
- TEST_MATRIX.md
- SCRIPTS_GUIDE.md (if scripts/automation)
- docs/decisions/* (latest ADRs)

## Definition of Done
- ✅ tests pass
- ✅ security checks pass (Semgrep + Gitleaks)
- ✅ no new high-severity findings introduced
- ✅ docs updated (only as needed)


## Multi-CLI + Delegator mode (Codex CLI / Gemini CLI / other)
This repo may be edited by multiple agentic tools. The delegator must:
- Route tasks by **risk + cost + context length** (see tools/ai/ROUTING_POLICY.md).
- Enforce **rate limits and daily budgets** for each provider (see tools/ai/BUDGETS.md).
- Prefer small, local operations first (grep, tests, linters) before spending model calls.

### Usage/telemetry hooks (manual)
- Codex CLI: use `/status` to view session config + token usage.
- Keep a lightweight log of agent calls in `tools/ai/call-log.ndjson` (append-only).

### Polyglot default
When the language/framework is not fixed:
- Detect the stack from repo files (see scripts/stack_detect.*).
- Choose the smallest viable toolchain for that stack.
- Update README.md with exact run/test/lint commands once detected.
