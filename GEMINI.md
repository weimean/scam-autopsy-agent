# Project DNA — Scam Autopsy

You are building **Scam Autopsy**, a *defensive* consumer-protection AI agent for the
Kaggle × Google 5-Day AI Agents capstone (Track: **Agents for Good**).

## Source of truth
- The `specs/` folder is the **source of truth**. **Read it before generating anything.**
  - `specs/00_architecture.md` — system design + agent graph
  - `specs/01_behaviors.feature` — Gherkin acceptance criteria (the behavioural contract)
  - `specs/02_taxonomy.md` — the manipulation-tactic taxonomy
  - `specs/03_schemas.md` — data + tool contracts (YAML)
- **Whenever you change code: update the relevant spec, extend the tests/eval, and update `README.md`.**
- Prefer clean Markdown for narrative + flat YAML for structured config (token-efficient).

## What this system does (one line)
A user forwards a suspicious message; a sandboxed red-team **Scammer** agent replays it
against a **Guardian** agent to extract the manipulation playbook, producing a verdict +
threat-intel report + protection guidance, and growing a shared tactic knowledge base.

## 🚨 Non-negotiable safety rules
1. **Defensive only.** NEVER produce operational, ready-to-send scam content. The Scammer
   agent is a *sandboxed red-team simulation*; every one of its outputs is prefixed
   `SIMULATION:` and is length-capped.
2. **Policy Server gates every Scammer/Report output** — structural check (SIMULATION label +
   length cap) AND a semantic check ("does this function as a deployable scam?"). Block + reframe on fail.
3. **Mask PII at intake** (emails, phone numbers, crypto wallets, names → placeholders like
   `[[EMAIL]]`, `[[PHONE]]`, `[[WALLET]]`). **Never persist raw user input.**
4. **No secrets in code.** Read `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, etc. from env vars.
5. Every user-facing report ends with a disclaimer ("educational, not legal/financial advice")
   and official reporting links.

## Engineering conventions
- Language: Python 3.11+. Framework: ADK 2.0 (graph workflow). Package mgr: `uv`.
- **Model routing:** `gemini-3.1-flash-lite` for high-volume nodes (Intake, Scammer, Guardian
  turns); `gemini-3.1-pro` for reasoning-heavy nodes (Tactic Extractor, Report Generator).
  ⚠️ Verify these model IDs are current before use; do not silently fall back to older ids.
- Bound the adversarial loop to **≤ 6 turns** with a token ceiling + timeout; on error/timeout,
  **degrade gracefully** to Report Generator using classifier hints.
- Comment code with the *why* (design/behaviour), not just the *what* — judged criterion.
- Build the **eval harness before** the agent logic (EDD).
