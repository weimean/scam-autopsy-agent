# 🛡️ Scam Autopsy

Forward it a scam message and it tells you three things: whether it's a scam, exactly how the message is trying to manipulate you, and what the scammer would do next if you replied. Everything it learns gets saved to a shared knowledge base, so the next person who checks a similar scam gets a better answer. An interactive web demo is available via Gradio to paste and analyze messages in your browser.

Built for the Kaggle × Google *5-Day AI Agents: Intensive Vibe Coding* Capstone. **Track: Agents for Good.**

> [Optional: add a sentence here on why you built this — e.g. a scam a friend or relative nearly fell for. A real reason lands better than any feature list.]

---

## The problem

Scams cost people billions a year, and the effective ones are engineered. They lean on specific psychological levers (urgency, fake authority, a slow build of false trust) that most of us can't name while a convincing message is sitting in front of us. The people who get hit hardest tend to be the ones with the least backup: an elderly parent, someone reading in their second language, anyone alone with a message and no one to ask. A generic "watch out for scams" leaflet doesn't help in that moment.

Scam Autopsy is meant to help in that moment. You paste the message, and you get a straight answer plus a breakdown of the manipulation, written in the language the message came in.

## Why agents, and not just one prompt

A single model call can guess "looks like a scam." It can't cross-examine one. So instead of asking the model for a verdict, I make two agents argue: a sandboxed red-team *Scammer* replays the pitch, and a *Guardian* pushes back and names each trick as it appears. That back-and-forth surfaces levers a one-shot prompt walks right past. Whatever new tactics show up get written to a shared knowledge base, so the tool gets a little sharper every time someone runs it.

That's the part that actually needs agents: several specialized roles, a tool they all share, memory that persists, and a safety layer deciding what's allowed to come out.

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
        │  Forecaster  │  (gated by the Policy Server: warnings, never scripts)
        └──────┬───────┘
        ┌──────▼───────┐
        │   Report     │  verdict · tactics · warning · how-to-protect ·
        │   Generator  │  escalation forecast · reporting links  (in the user's language)
        └──────────────┘
```

If the adversarial loop errors out or runs long, the graph skips straight to the Report Generator using the classifier's hints, so a verdict and a warning always come back.

## Course concepts demonstrated

| Concept | Where | How |
| --- | --- | --- |
| **Multi-agent system (ADK)** | Code | 6-stage ADK graph plus the Scammer⇄Guardian adversarial loop |
| **MCP Server** | Code | `scam-intel` SQLite MCP server (`query_tactics` / `add_tactic` / `get_stats`) the agents read from and write to |
| **Antigravity** | Video | The whole thing was vibe-coded in Antigravity from a `specs/` source of truth |
| **Security features** | Code + Video | PII masking at intake, a two-layer Policy Server, and a safety eval it passes 100% |
| **Deployability** | Video / Docs | Agent Runtime + Cloud Run steps documented below and reproducible |
| **Agent skills (Agents CLI)** | Code | Scaffolded, evaluated, and deployed with `google-agents-cli` |

## Evaluation

I wrote the eval harness before the agents, so every step of the build had a number to move rather than a vibe to chase.

| Metric | Result | Sample | Notes |
| --- | --- | --- | --- |
| Classifier F1 | **94.74%** | n=100 | Scored on public data (UCI SMS Spam Collection), not my own examples |
| False-positive rate | **11.11%** | n=100 | Tuned to err toward catching scams over staying quiet |
| Tactic-extraction quality | **3.52 / 5.0** | n=21 | Independent LLM-as-judge (`gemini-2.5-pro` grading the agents). The extractor tends to *over-extract* — it names levers beyond the ground truth, which the judge penalizes — though the taxonomy stays constrained to valid Pydantic `Literal`s |
| Safety policy success | **100%** | n=11 | 8 offensive-content attacks blocked, 2 benign defensive requests allowed, 1 forecast injection blocked |

### How I kept the numbers honest

This is the part I'm most proud of, because a green scorecard is easy to fake yourself into.

- **I scored the classifier on outside data.** Public SMS-spam messages, not the cases I wrote, so a good F1 means it generalizes instead of memorizing my test set.
- **The judge is a different model from the agents** (on Vertex, `gemini-2.5-pro` grading `gemini-3.1` agents). The free-tier run collapses everything to one model to survive the quota, and I say so rather than hide it.
- **I caught myself gaming my own eval.** An early scorecard read "100%" because it was quietly running on 3 cases. I noticed, expanded it to the full set, and the real F1 is the 94.74% above.
- **I caught the safety layer over-blocking.** The escalation forecaster started censoring its own *warnings to the victim* as if they were scam scripts. I retuned the semantic gate to tell a warning apart from a script, then re-ran the safety suite to confirm the real attacks still get blocked.

## Hardening it: the bug my fail-safe was hiding

The scorecard above is honest about *what it measured* — but going back to harden the system taught me something the numbers couldn't.

I built the graph to degrade gracefully: if the adversarial loop errors or runs long, it skips to the Report Generator on the classifier's hints, so a verdict always ships. That fail-safe worked a little too well. When I finally instrumented the Scammer⇄Guardian loop, I found it had been **crashing on the second turn of every run** — I was appending `AdversarialTurn` objects to the history, but the agents expected plain dicts and called `.get()` on them. The loop died, the fail-safe swallowed it, the report still looked right, and the eval — which grades the *final output* — never noticed. My own graceful degradation was hiding a dead loop.

Fixing the crash surfaced a more interesting problem: even with the loop running, every Scammer turn came back blocked — and it *should* have. I'd told the red-team to **generate** the scam pitch, which is exactly the deployable-scam text my own Policy Server exists to refuse. The two halves of the design were fighting each other. The fix was conceptual, not mechanical: a defensive red-team shouldn't *write* scams, it should **expose the next manipulation move and name the lever** — analysis that surfaces the tactic without ever producing something sendable. That clears the safety gate and gives the Guardian something real to name. (One last wrinkle: the Guardian kept coming back empty on the smaller model until I trimmed the piled-up scam history out of its prompt — the stack of tactic descriptions was tripping the model's own safety filter.)

The loop runs end to end now: six turns, both agents populated, the manipulation playbook surfaced move by move — fear, authority, reciprocity, scarcity, trust-building — and those tactics flow into the report instead of coming from a fallback.

**I re-ran the whole suite after these fixes** (on Vertex, with the independent `gemini-2.5-pro` judge), and the honest picture shifted. The classifier F1 held (**94.74%**), the false-positive rate rose a little (**11.11%**), safety stayed at **100%** — and tactic-extraction quality came in at **3.52/5**, not the 5.0 an earlier run showed. That earlier perfect score had leaned on a mock judge that quietly returned near-ground-truth answers whenever the real judge hit a quota wall; once I stopped it inflating the number, the truth is that the extractor **over-extracts** — it names levers beyond what's really there. Lower, but real — and it points straight at the next thing to fix.

## Safety design

The system holds a red-team agent that talks like a scammer, so I treated safety as part of the build, not a wrapper on top of it.

1. **Defensive only.** The Scammer agent is sandboxed, every line it emits is `SIMULATION:`-labelled and length-capped, and the tool never hands back a message you could actually send.
2. **A two-layer Policy Server.** One structural check (the label and length) and one semantic check that asks whether the text would work as a real scam, running on the Scammer, forecast, and report outputs. Anything that fails gets blocked and reframed.
3. **PII masked at intake.** Emails, phones, wallets, and URLs become placeholders before any agent or the database sees them, and the raw message is never stored.
4. **Every report ends with a disclaimer and real reporting links** (FTC, IC3, and local equivalents).

## Setup

> Needs Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and a Gemini API key. Nothing sensitive lives in the code; keys come from environment variables.

```bash
git clone <your-repo-url> && cd scam-autopsy
uv sync                                  # install dependencies
export GEMINI_API_KEY="your-key"         # an AI Studio key on the free tier is enough
# optional, for Vertex + an independent judge:
# export GOOGLE_CLOUD_PROJECT="your-project"

# analyze a single message
# (on a free AI Studio key, prefix GOOGLE_GENAI_USE_VERTEXAI=False so it doesn't route to Vertex)
GOOGLE_GENAI_USE_VERTEXAI=False uv run python -m app.agent --message "Your account will be suspended in 24h, verify at http://..."

# run the interactive web demo
uv run python -m app.ui

# run the full evaluation suite
make grade
```

## Deployment (reproducible)

The agent is ready for Agent Runtime. To put the stateful backend and a Cloud Run front end in the cloud:

```bash
agents-cli scaffold enhance --deployment-target agent_runtime --yes   # add prod wrappers
uv lock
agents-cli deploy --dry-run                                           # validate first
agents-cli deploy --project "$GOOGLE_CLOUD_PROJECT" --region us-west1 # ~5–10 min
```

`deployment_metadata.json` holds the Agent Runtime ID, and traces stream to Cloud Trace on their own.

## Project structure

```
scam-autopsy/
├── specs/            # source of truth: architecture, Gherkin behaviours, taxonomy, schemas
├── app/
│   ├── agent.py      # ADK graph wiring
│   ├── ui.py         # lightweight Gradio presentation UI
│   ├── nodes/        # intake · adversarial · extractor · forecaster · generator
│   ├── guardrails/   # two-layer Policy Server + PII masking
│   └── schemas.py    # Pydantic contracts
├── mcp/              # scam-intel MCP server (SQLite)
├── eval/             # datasets + eval_config.yaml + load_datasets.py
└── tests/
```

## What I'd build next

- A URL and domain reputation tool (over MCP) so a verdict rests on live evidence, not just the model's read.
- Vector search across the knowledge base, so the tool can say "this is close to N scams I've already seen."
- An A2A hook so a separate reporting or compliance agent can pull an autopsy on its own.

---

## License

© 2026 Tsoi Wai Mun — *Scam Autopsy*. Licensed under [CC BY 4.0](LICENSE). Reuse and adapt it freely; just keep the attribution. The classifier evaluation set includes messages drawn from the public [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (Almeida & Gómez Hidalgo, freely available for research — please cite it if you reuse the data); the tactic and safety sets are hand-labeled by the author. The CC BY 4.0 license covers my own work, not the underlying public corpora.

---

*Built with Google Antigravity, ADK 2.0, Agents CLI, and the Model Context Protocol. It's an educational tool, not legal or financial advice.*
