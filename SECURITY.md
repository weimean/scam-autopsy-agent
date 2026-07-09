# Security Policy

Scam Autopsy is a **defensive** security tool. It analyzes scam messages to help
people recognize manipulation; it is designed never to produce content that could
be used to carry out a scam.

## Reporting a vulnerability

If you find a security issue — especially anything that lets the system emit
sendable scam content, leak the raw (unmasked) input, or bypass the Policy Server
— please report it privately rather than opening a public issue.

- Use GitHub's **[Report a vulnerability](https://github.com/weimean/scam-autopsy-agent/security/advisories/new)**
  (Security → Advisories) to open a private advisory, or
- contact the maintainer at the email listed in `pyproject.toml`.

Please include steps to reproduce, the message or input that triggers it, and the
observed vs. expected behavior. We aim to acknowledge reports within a few days.

## Safety model

These are the invariants the project treats as security-critical. Regressions in
any of them are in scope for a report:

1. **Defensive only.** The red-team *Scammer* agent is sandboxed. Every line it
   emits is `SIMULATION:`-labelled and length-capped, and the tool never returns a
   message that could be sent as an actual scam.
2. **Two-layer Policy Server.** A structural check (label + length) and a semantic
   check (would this text work as a real scam?) run over the Scammer, forecast, and
   report outputs. Anything that fails is blocked and reframed.
3. **PII masked at intake.** Emails, phone numbers, URLs, and crypto wallets are
   replaced with placeholders before any agent or the database sees them. The raw
   message is never stored.
4. **No secrets in the repo.** API keys and cloud credentials come only from
   environment variables (see `.env.example`).

## Scope

This is an educational project and provides no warranty. It is not legal or
financial advice. Reports about the *content* of third-party scam corpora used for
evaluation (e.g. the public UCI SMS Spam Collection) are out of scope.
