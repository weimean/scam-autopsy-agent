# 03 — Data & tool contracts (source of truth)

Deeply-nested config in YAML (token-efficient per the SkCC finding); narrative in Markdown.

## Classifier output (Intake node)
```yaml
classifier_output:
  is_scam: bool
  confidence: float        # 0.0–1.0
  category: str            # one of 02_taxonomy.md categories, or "unknown"
  red_flag_hints: [str]    # cheap surface signals; also feeds graceful degradation
  masked_text: str         # PII already replaced with placeholders
  detected_language: str   # ISO 639-1 code (e.g. "en", "es", "fr"); detected at intake
```

## PII placeholders (applied at intake, before anything else)
```yaml
pii_placeholders:
  email: "[[EMAIL]]"
  phone: "[[PHONE]]"
  wallet: "[[WALLET]]"      # crypto addresses
  url: "[[URL]]"
  person_name: "[[NAME]]"
  amount: "[[AMOUNT]]"
rule: "mask before any agent or the KB sees the text; never persist raw input"
```

## scam-intel MCP server — SQLite table + tools
```yaml
tactic_kb_table:            # table: tactics
  id: int (pk, autoincrement)
  name: str (unique with category)
  category: str
  lever: str
  description: str
  example_masked: str

mcp_tools:
  query_tactics:
    args: {category: str}
    returns: "list[tactic]"          # Guardian reads to name known levers
  add_tactic:
    args: {name: str, category: str, lever: str, description: str, example_masked: str}
    returns: "{added: bool, reason: str}"   # dedup on (name, category)
  get_stats:
    args: {}
    returns: "{total: int, by_category: dict}"
```

## Report Generator output (the final contract)
```yaml
report:
  verdict:
    is_scam: bool
    confidence: float
    category: str
  tactics:                  # what the adversarial autopsy surfaced
    - name: str
      lever: str
      explanation: str      # plain language, for a non-expert
  warning: str              # 1–2 sentence plain-language bottom line
  how_to_protect: [str]     # concrete steps
  reporting_links:          # official channels
    - {label: str, url: str}
  disclaimer: str           # "educational, not legal/financial advice"
  kb_stat: str              # "tactics catalogued: N" — collective-intelligence signal
  language: str             # ISO 639-1 code; report is written in this language
```

## Adversarial loop control
```yaml
loop_bounds:
  max_turns: 6
  token_ceiling: 8000       # across the loop; tune during eval
  timeout_seconds: 60
on_exceed: "degrade — skip to Report Generator using classifier red_flag_hints"
```

## Policy Server (guardrail) contract
```yaml
policy_server:
  structural:
    scammer_output_must_start_with: "SIMULATION:"
    scammer_output_max_chars: 600
  semantic:
    model: "gemini-3.1-pro"    # verify id is current
    prompt: "Does this text function as a deployable scam a user could send to a victim? Answer VIOLATION or OK."
    on_violation: "block + reframe as defensive intel"
```
