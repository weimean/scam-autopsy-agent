# 02 — Manipulation-tactic taxonomy (source of truth)

Two axes: the **persuasion lever** (why it works on the brain) and the **fraud category**
(what kind of scam). The Guardian names the lever; the Extractor tags both.

## Persuasion levers (Cialdini + fraud-specific)
| lever | definition |
| --- | --- |
| authority | impersonates a trusted institution/official (bank, IRS, CEO, police) |
| urgency | manufactured time pressure ("act in 24h or lose it") to bypass reflection |
| scarcity | artificial limited supply / exclusivity ("only 5 spots left") |
| social_proof | fake testimonials, "everyone's investing", forged screenshots of profits |
| reciprocity | small gift/favour first to create obligation |
| liking | flattery, feigned romance/friendship to lower defences |
| commitment | tiny first ask, then escalate (foot-in-the-door) |
| fear | threats — arrest, account closure, exposure — to force compliance |
| unrealistic_returns | promises of guaranteed/outsized profit with no risk |
| trust_building | slow rapport over days/weeks before the ask (romance/pig-butchering) |
| isolation | discourage victim from consulting family/bank/authorities |

## Fraud categories
| category | definition | common red flags |
| --- | --- | --- |
| crypto_investment | fake trading platforms / tokens promising high returns | wallet address, "guaranteed" ROI, withdrawal fees |
| romance | long-con emotional manipulation → money request | fast intimacy, never video-calls, sudden crisis/opportunity |
| phishing | credential/data theft via impersonation + link | urgent "verify your account", mismatched sender/link |
| prize_lottery | "you won" → pay a fee/taxes to claim | you never entered, upfront fee to release winnings |
| tech_support | fake support claiming your device is infected | unsolicited "virus" alert, remote-access request |
| advance_fee | pay a small sum now to unlock a large payout later (419) | inheritance/beneficiary story, upfront transfer |
| impersonation_bec | pose as boss/vendor to redirect a payment | urgent wire change, "keep this confidential" |

## Seed tactics (also seed the scam-intel MCP KB)
name | category | lever | description | example_masked
--- | --- | --- | --- | ---
guaranteed_returns | crypto_investment | unrealistic_returns | promises risk-free outsized profit | "lock in 300% in a week, zero risk"
withdrawal_fee_trap | crypto_investment | commitment | lets you "win" then demands a fee to withdraw | "pay [[AMOUNT]] release fee to unlock your balance"
deadline_pressure | phishing | urgency | short fuse to stop you verifying | "account suspended in 24h — verify now"
account_verify_link | phishing | authority | poses as the bank + a lookalike link | "confirm your details at [[URL]]"
you_have_won | prize_lottery | scarcity | unclaimed prize you never entered for | "claim your [[AMOUNT]] before it expires"
release_fee | prize_lottery | reciprocity | small fee to release big winnings | "pay [[AMOUNT]] processing to receive [[AMOUNT]]"
love_bomb | romance | liking | rapid intense affection to lower guard | "I've never felt this way, you're my soulmate"
crisis_ask | romance | urgency | sudden emergency needing money | "customs is holding my package, send [[AMOUNT]]"
dont_tell_anyone | romance | isolation | discourages outside advice | "our bank wouldn't understand, keep this between us"
infected_device | tech_support | fear | fake infection to force remote access | "your device is compromised, install [[APP]]"
inheritance_beneficiary | advance_fee | authority | official-sounding windfall story | "you are the beneficiary of [[AMOUNT]], send fees"
urgent_wire_change | impersonation_bec | authority | posing as boss/vendor to redirect payment | "new bank details, wire today, keep confidential"

> Extend this table as the KB grows. Keep examples **masked** — no real PII, no operational scripts.
