# 00 — Architecture (source of truth)

## Purpose
Put scam-analysis expertise in ordinary people's hands. A user forwards a suspicious
message; the system returns a **verdict**, a **threat-intelligence report** (every
manipulation tactic used), **plain-language protection guidance**, and grows a shared
**tactic knowledge base** that protects future victims. Track: **Agents for Good**.

## Novel mechanism
A sandboxed red-team **Scammer** agent replays the pitch against a **Guardian** agent; the
adversarial exchange surfaces manipulation levers a single prompt would miss. **No real
person is ever contacted** — the adversary is a simulation.

## Agent graph (ADK 2.0 workflow)
```
        ┌─────────────┐
INPUT → │  Intake &    │  normalize message, mask PII → placeholders
        │  Classifier  │  → {is_scam, confidence, category, red_flag_hints[]}
        └──────┬───────┘
               │ (only if is_scam and confidence ≥ 0.5)
        ┌──────▼───────┐
        │  Adversarial │  bounded loop, N ≤ 6 turns:
        │  Core:       │  Scammer replays pitch (SIMULATION:) ⇄
        │  Scammer ⇄   │  Guardian counters, names the lever, probes next
        │  Guardian    │  → transcript of surfaced tactics
        └──────┬───────┘
        ┌──────▼───────┐
        │   Tactic     │  map transcript → taxonomy (see 02_taxonomy.md)
        │   Extractor  │  dedup vs KB; write NEW tactics → scam-intel MCP
        └──────┬───────┘
        ┌──────▼───────┐
        │  Escalation  │  read transcript + tactics, predict future path
        │  Forecaster  │  exclusively from victim's perspective (defensive warning)
        └──────┬───────┘
        ┌──────▼───────┐
        │   Report     │  verdict + tactics + plain-language warning
        │   Generator  │  + how-to-protect + reporting links + disclaimer
        └──────────────┘
```
```

## Components (see 03_schemas.md for I/O contracts)
| Node | Role | Model |
| --- | --- | --- |
| Intake/Classifier | normalize, mask PII, classify | flash-lite |
| Scammer (red-team) | sandboxed replay to surface tactics; outputs `SIMULATION:` + length-capped | flash-lite |
| Guardian (blue-team) | counter each move, name the lever, probe; reads scam-intel MCP | flash-lite |
| Tactic Extractor | map transcript → taxonomy; dedup; write new tactics → MCP | pro |
| Escalation Forecaster | predict future path defensively, route via Policy Server | pro |
| Report Generator | assemble the report contract | pro |

## `scam-intel` MCP server (SQLite, stdio)
Tools: `query_tactics(category)` (Guardian reads) · `add_tactic(...)` with dedup on
`(name, category)` (Extractor writes) · `get_stats()` → "tactics catalogued: N" for the UI.
KB **persists globally**; per-case state (transcript, tactics) lives in the session.

## Guardrails (structural + semantic Policy Server — see GEMINI.md rules)
1. Input hygiene: mask PII at intake, never persist.
2. Output gating: structural (`SIMULATION:` label + length cap on Scammer) + semantic
   ("does this function as a deployable scam?" → block + reframe).
3. Loop bounding: N ≤ 6, token ceiling, timeout → graceful degradation.
4. Mandatory disclaimer + reporting links on every report.

## Graceful degradation
If the adversarial loop errors or exceeds its bounds, skip Core and go Classifier →
Report Generator using `red_flag_hints`. A verdict + warning **always** ship.

## Multi-language analysis
- **Intake** detects the message language (ISO 639-1 code) and stores it as
  `detected_language` in `classifier_output`.
- **Analysis runs in the original language.** Gemini is natively multilingual; there is
  no forced translation step. PII regex masking is already language-agnostic.
- **Taxonomy is language-agnostic.** Lever names and categories (e.g. `urgency`,
  `phishing`) remain English identifiers regardless of input language.
- **Report Generator writes the report in the detected language**, so a non-English
  speaker gets a warning, how-to-protect steps, and disclaimer they can actually read.

## Evaluation (build FIRST — EDD; see blueprint §4 Phase 2)
- **Classifier F1 + false-positive-rate** on a PUBLIC dataset (UCI SMS Spam + aggregated
  Kaggle phishing CSV + SpamAssassin/Enron ham) — de-biases the headline metric.
- **Tactic-extraction 0–5** via LLM-as-judge (a *different* model than the agents).
- **Safety**: 100%-block on a red-team set (force a deployable script / PII leak).

## Course concepts demonstrated (≥3 required; we target 6)
Multi-agent ADK (this graph) · MCP server (`scam-intel`) · Antigravity (build, shown in video)
· Security (PII mask + Policy Server) · Deployability (Agent Runtime/repro docs) · Agent Skills (Agents CLI).

## Tech stack
Python 3.11+ · ADK 2.0 · `uv` · MCP Python SDK · SQLite · (stretch) FastAPI on Cloud Run,
backend on Agent Runtime. Secrets via env vars only.

## Optional Front End
- **Gradio Demo UI** (`app/ui.py`): A thin presentation layer that calls the existing agent pipeline and renders the final report interface (verdict, language, tactics, forecast, protective steps, statistics, and raw JSON). It functions purely as a presentation wrapper and does not modify any backend agent logic, nodes, or guardrails.

