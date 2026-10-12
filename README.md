# cardopt: which card should I use for this purchase?

Tell it which cards you carry (product names only, never card numbers) and what you're buying. It ranks your cards and shows the math.

**Design principle:** an agent handles judgment (what is this purchase? which channel?); a deterministic engine handles the math. The LLM never computes rewards.

## Status

| Phase | What | State |
|---|---|---|
| 0-1 | Repo, card knowledge base (5 sample cards), schema validator | done |
| 2 | Deterministic ranking engine, CLI, tests (14 passing) | done |
| 3 | Classification agent (free text -> category, channel, confidence) | next |
| 4 | Orchestration, clarifying questions, nudges (portal, unused credits) | |
| 5 | Eval set (25-30 scenarios) | |
| 6 | Rules-extraction agent (issuer page -> card JSON) | |
| 7 | Chrome extension (checkout trigger + deep-dive panel) | |

## Run it

```bash
pip install -e ".[dev]"          # or: set PYTHONPATH=src
python -m cardopt.cli --cards "csr, amex gold, citi" --category dining --amount 50
python -m cardopt.cli --cards "csr, vx" --category hotels --channel portal --json
python -m cardopt.validate       # schema-check card files
pytest
```

`--json` output is what the extension's "why this card" panel will render.

## Privacy by design

Stores only card product names. No numbers, expiry, CVV, or account links.

## Known limitations (be upfront about these)

- **Card data is AI-drafted from issuer pages and not yet human-verified.** 17 cards, each rule carries a `source_url` and `source_quote`. Every card has `last_verified: null`, and the engine says so in its caveats. Cards read from secondary sources only (none now that Chase Sapphire Reserve was re-read from Chase) and Discover's rotating categories are the weakest. Spot-check before trusting a result. Previous hand-written versions are in `data/superseded/`.
- Co-brand and merchant-specific cards are out of scope for now (parked in `data/parked_cobrand/`); the engine's merchant-rule support is dormant.
- Point values are flat assumptions per currency (`valuations.py`), not real redemption values. Override with `--cpp chase_ur=2.0`.
- No cross-card point pooling (e.g. Freedom points worth more next to a Sapphire).
- Rotating quarterly categories not modeled.
- Real merchant category codes (MCC) are only known after purchase, so category is a probabilistic guess. Phase 3 will report confidence and a fallback.
- Annual fees and statement credits are shown but not factored into per-purchase ranking.
