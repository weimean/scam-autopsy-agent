# 🛡️ Scam Autopsy

**A defensive, multi-agent AI system that dissects a scam message a user forwards — exposing every manipulation tactic, forecasting how the scam would escalate, and growing a shared knowledge base that protects future victims.**

Built for the Kaggle × Google *5-Day AI Agents: Intensive Vibe Coding* Capstone · **Track: Agents for Good**

---

## The problem

Scams cost people billions every year, and the ones that work best are *engineered* — they exploit specific psychological levers (urgency, authority, fabricated trust) that a non-expert can't easily name in the moment. Victims are often the least-defended: elderly relatives, non-native speakers, people alone with a convincing message and no one to ask. A static "watch out for scams" tip sheet doesn't help when a message is in front of you *right now*.

**Scam Autopsy** turns scam-analysis expertise into something anyone can use: forward a suspicious message, get back a verdict, a plain-language breakdown of exactly how it's trying to manipulate you, a forecast of what the scammer would do next, and concrete steps to protect yourself — in your own language.

## Why agents (not a single prompt)?

A single LLM call can *guess* "this looks like a scam." It can't **interrogate** one. Scam Autopsy runs a bounded **adversarial loop**: a sandboxed red-team *Scammer* agent replays the pitch against a *Guardian* agent, and that exchange surfaces manipulation levers a one-shot prompt misses. The tactics it discovers are written to a shared knowledge base — so every scam analyzed makes the system smarter for the next person. That's a genuinely agentic problem: multiple specialized agents, tool use, memory, and safety gating working together.

## Architecture

```
        ┌─────────────┐
INPUT → │  Intake &    │  detect language · mask PII · classify
        │  Classifier  │  → {is_scam, confidence, category, language, hints[]}
        └──────┬───────┘
               │ (if likely scam)
        ┌──────▼───────┐
        │  Adversarial │  bounded loop, ≤6 turns:
        │  Scammer ⇄   │  sandboxed red-team Scammer (SIMULATION-labelled) ⇄
        │  Guardian    │  Guardian counters, names the lever, queries the KB
        └──────┬───────┘
        ┌──────▼───────┐
        │   Tactic     │  map transcript → taxonomy (Cialdini levers + fraud type)
        │   Extractor  │  dedup + write NEW tactics → scam-intel MCP knowledge base
        └──────┬───────┘
        ┌──────▼───────┐
        │  Escalation  │  victim-side forecast of how the scam would escalate
        │  Forecaster  │  (gated by the Policy Server — warnings, never scripts)
        └──────┬───────┘
        ┌──────▼───────┐
        │   Report     │  verdict · tactics · warning · how-to-protect ·
        │   Generator  │  escalation forecast · reporting links  (in the user's language)
        └──────────────┘
```

**Graceful degradation:** if the adversarial loop errors or exceeds its bounds, the graph skips to the Report Generator using the classifier's hints — a verdict and warning always ship.

## Course concepts demonstrated

| Concept | Where | How |
| --- | --- | --- |
| **Multi-agent system (ADK)** | Code | 6-stage ADK graph + the Scammer⇄Guardian adversarial loop |
| **MCP Server** | Code | `scam-intel` SQLite MCP server (`query_tactics` / `add_tactic` / `get_stats`) that the agents read *and grow* |
| **Antigravity** | Video | Entire system vibe-coded in Antigravity from a `specs/` source of truth |
| **Security features** | Code + Video | PII masking at intake · two-layer Policy Server (structural + semantic) · 100% adversarial-safety eval |
| **Deployability** | Video / Docs | Agent Runtime + Cloud Run deployment path documented below (reproducible) |
| **Agent skills (Agents CLI)** | Code | Built and evaluated with `google-agents-cli` (scaffold / eval / deploy skills) |

## Evaluation

Built **evaluation-first** (the harness before the agents), so every implementation step was measured against an objective target.

| Metric | Result | Sample | Notes |
| --- | --- | --- | --- |
| Classifier F1 | **94.34%** | n=100 | On **public** data (UCI SMS Spam Collection), not self-authored cases |
| False-positive rate | **8.33%** | n=100 | Deliberate precision/recall trade-off toward catching scams |
| Tactic-extraction quality | **5.0 / 5.0** | n=18 | LLM-as-judge; extraction constrained to valid taxonomy levers via Pydantic `Literal`s. Out-of-distribution review (fresh scams) confirms sensible extraction |
| Safety policy success | **100%** | n=11 | 8 offensive-content attacks blocked · 2 benign defensive requests allowed · 1 forecast-injection blocked |

### Evaluation integrity (how the numbers were kept honest)
- **Classifier bias:** validated on an *external public* dataset, not the project's own examples, to avoid overfitting to self-authored tests.
- **Judge independence:** on Vertex AI the LLM-as-judge (`gemini-2.5-pro`) is a *different* model from the agents; the free-tier run routes all roles to one model to respect quota, which is disclosed.
- **Small-sample honesty:** an early scorecard showed a misleading "100%" on a 3-case slice; it was caught and replaced with the full-set run reported above.
- **Guardrail calibration:** the escalation forecaster initially over-blocked its own *defensive* warnings (false positives); the semantic gate was recalibrated to allow victim-side warnings while still blocking offensive generation — re-verified at 100% safety.

## Safety design

This system deliberately contains a red-team agent that *speaks like a scammer*, so safety is a core feature, not an afterthought:
1. **Defensive-only.** The Scammer agent is sandboxed; every output is `SIMULATION:`-labelled and length-capped. The system never emits a ready-to-send scam.
2. **Two-layer Policy Server.** *Structural* gate (label + length) plus a *semantic* gate ("does this function as a deployable scam?") on Scammer, forecast, and report outputs — blocks and reframes on violation.
3. **PII masking at intake.** Emails, phones, wallets, URLs → placeholders before any agent or the KB sees them; raw input is never persisted.
4. **Mandatory disclaimer + reporting links** (FTC / IC3 / local) on every report.

## Setup

> Requires Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and a Gemini API key. **No secrets are stored in the code — everything is read from environment variables.**

```bash
git clone <your-repo-url> && cd scam-autopsy
uv sync                                  # install dependencies
export GEMINI_API_KEY="your-key"         # AI Studio key (free tier works)
# (optional, for Vertex + independent judge) export GOOGLE_CLOUD_PROJECT="your-project"

# run the agent locally on a message
uv run python -m app.agent --message "Your account will be suspended in 24h, verify at http://..."

# run the full evaluation suite
make grade
```

## Deployment (reproducible)

The agent is Agent-Runtime-ready. To deploy the stateful backend and a Cloud Run front end:

```bash
agents-cli scaffold enhance --deployment-target agent_runtime --yes   # add prod wrappers
uv lock
agents-cli deploy --dry-run                                           # validate
agents-cli deploy --project "$GOOGLE_CLOUD_PROJECT" --region us-west1 # provision (~5–10 min)
```
`deployment_metadata.json` records the Agent Runtime ID; telemetry streams automatically to Cloud Trace.

## Project structure

```
scam-autopsy/
├── specs/            # source of truth: architecture, Gherkin behaviours, taxonomy, schemas
├── app/
│   ├── agent.py      # ADK graph wiring
│   ├── nodes/        # intake · adversarial · extractor · forecaster · generator
│   ├── guardrails/   # two-layer Policy Server + PII masking
│   └── schemas.py    # Pydantic contracts
├── mcp/              # scam-intel MCP server (SQLite)
├── eval/             # datasets + eval_config.yaml + load_datasets.py
└── tests/
```

## What I'd build next
- A URL/domain-reputation MCP tool to ground verdicts in live evidence.
- Vector search over the growing knowledge base ("this scam is 87% similar to N others seen").
- An A2A hook so a compliance/reporting agent can consume the autopsy.

---

*Built with Google Antigravity, ADK 2.0, Agents CLI, and the Model Context Protocol. Educational tool — not legal or financial advice.*
