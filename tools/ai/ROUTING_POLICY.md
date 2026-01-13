
# Routing Policy (Delegator)

Goal: maximize throughput under multiple usage limits while keeping quality gates.

## Task classes
1) **Local-first** (no model calls):
   - grep/ripgrep, tree, find, build/test, lint, typecheck, run SAST/secret scan, generate SBOM.

2) **Cheap-model tasks** (small context, low risk):
   - naming, docs, comments, small refactors, unit tests scaffolding, simple bugfixes.

3) **Strong-model tasks** (complex reasoning, higher risk):
   - auth model changes, data migrations, concurrency, security hardening, architecture decisions, incident response.

4) **Research tasks**
   - framework-specific defaults, breaking changes, CVEs, cloud quotas/limits.

## Default routing
- If change touches **authZ / permissions / tenant boundaries** → strong model + mandatory negative tests.
- If change touches **payments / PII / exports** → strong model + review + extra logging redaction checks.
- If task is “summarize / outline / propose options” → cheap model.
- If request needs web citations → Perplexity or Gemini (search-enabled), then implement locally.

## Guardrails
- Hard cap: keep autonomous loops under N steps unless explicitly overridden.
- Always run: tests (or at least a smoke command) before finalizing.
- If provider returns 429/rate limit → backoff and switch to next provider, preserving state.
