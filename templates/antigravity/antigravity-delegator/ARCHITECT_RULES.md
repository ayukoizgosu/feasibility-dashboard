# THE GOD STACK — Vibe Coding Workflow

**Quota semantics (keep accurate):**
- **Antigravity Free**: typically **weekly** quota window.
- **Antigravity Pro/Ultra**: quota windows that **refresh ~every 5 hours** (per vendor comms; can occasionally display inconsistently).
- Usage is usually measured as **"work done"** (complex reasoning burns faster than simple tasks).

---

## THE BIG THREE

| Role | Primary Model | Usage | Best For |
|------|---------------|-------|----------|
| **🏛️ Architect** | Claude Opus 4.5 (Thinking) | 10% | Planning, TODO.md, hard bugs |
| **🔨 Builder** | GPT-5.2-Codex (Codex CLI) | 80% | Writing code from plan |
| **🧹 Janitor** | Gemini CLI (Flash/Pro) | Unlimited | Tests, linting, explanations |

---

## REDUNDANCY / FALLBACK CHAINS

When a model hits its quota limit, switch to the next available:

### 🏛️ Architect Fallback Chain
```
Claude Opus 4.5 (Thinking)  [PRIMARY]
    ↓ exhausted
Claude Sonnet 4.5 (Thinking)
    ↓ exhausted
GPT-5.2 (Codex CLI)
    ↓ exhausted
Gemini 3 Pro (High)
```

### 🔨 Builder Fallback Chain
```
GPT-5.2-Codex (Codex CLI)  [PRIMARY]
    ↓ exhausted
GPT-5.2-Codex-Max (Codex CLI)
    ↓ exhausted
GPT-5.1-Codex-Mini (Codex CLI)
    ↓ exhausted
Gemini CLI (gemini chat)
    ↓ exhausted
Claude Sonnet 4.5 (Antigravity)
```

### 🧹 Janitor Fallback Chain
```
Gemini CLI (Flash/Pro)  [PRIMARY]
    ↓ exhausted
GPT-5.1-Codex-Mini (Codex CLI)
    ↓ exhausted
GPT-OSS 120B (Medium) (Antigravity)
```

### 🏃 Marathon Runner Fallback
```
GPT-5.1-Codex-Max (Codex CLI)  [PRIMARY]
    ↓ exhausted
GPT-5.2-Codex (Codex CLI)
    ↓ exhausted
Claude Opus 4.5 (Thinking) — split into smaller tasks
```

---

## EXECUTION PROTOCOL

### Step 1: PLAN (Architect)
Use Claude Opus 4.5 (Thinking) to create the plan:
```
Create a TODO.md for implementing [feature]
```
**If exhausted:** Fall back to Sonnet → GPT-5.2 → Gemini Pro

### Step 2: BUILD (Builder via Codex CLI)
```bash
codex -c CODEX.md "Implement [function] per TODO.md" > src/file.ts
python quality_gate.py src/file.ts
```
**If exhausted:** Fall back to Codex-Max → Codex-Mini → Gemini CLI

### Step 3: CLEAN (Janitor via Gemini CLI)
```bash
gemini chat -c GEMINI.md "Write tests for src/file.ts" > tests/file.test.ts
```
**If exhausted:** Fall back to Codex-Mini → GPT-OSS 120B

---

## QUOTA OPTIMIZATION

| Request Type | Primary | Fallback 1 | Fallback 2 |
|--------------|---------|------------|------------|
| Multi-file planning | Opus | Sonnet (Thinking) | GPT-5.2 |
| Code generation | Codex CLI | Gemini CLI | Sonnet |
| Unit tests | Gemini CLI | Codex-Mini | GPT-OSS |
| Explain code | Gemini CLI | Codex-Mini | Any |
| Hard debugging | Opus | Sonnet (Thinking) | GPT-5.2 |

---

## REMEMBER

* **Check quota status** before selecting model
* **Switch immediately** when quota exhausted — no retries on same model
* **External CLIs first** (Codex/Gemini) — preserve Antigravity tokens
* **Quotas reset every 5 hours** — track first-use time


## TOOLING NOTES (delegator reliability)
- Prefer **external CLIs first** (Codex CLI / Gemini CLI) to preserve Antigravity quota.
- Codex CLI:
  - `/init` scaffolds **AGENTS.md**.
  - `/status` shows current session configuration (and may include usage telemetry depending on version).
  - Enable session logging if you want durable usage accounting.
- Gemini CLI:
  - Install: `npm install -g @google/gemini-cli`
  - Run: `gemini` / `gemini chat ...`