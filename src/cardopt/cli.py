"""CLI wrapper around the engine.

Example:
  python -m cardopt.cli --cards "csr, amex gold, citi" --category dining --amount 50
  python -m cardopt.cli --cards "csr, vx" --category hotels --channel portal --json

Phase 3 will add --purchase "Resy dinner deposit" (agent-classified category).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import rank_cards, to_dict
from .loader import DEFAULT_DATA_DIR, UnknownCardError, find_cards, load_cards
from .merchants import resolve_merchant
from .models import CATEGORIES, CHANNELS


def _parse_cpp(items):
    out = {}
    for item in items or []:
        key, _, val = item.partition("=")
        out[key.strip()] = float(val)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cardopt", description=__doc__.split("\n")[0])
    p.add_argument("--cards", required=True, help="Comma-separated cards you carry")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--channel", default="direct", choices=CHANNELS)
    p.add_argument("--merchant", help="Merchant name or domain, e.g. amazon or amazon.com")
    p.add_argument("--amount", type=float, help="Purchase amount in USD")
    p.add_argument("--cpp", action="append", metavar="CURRENCY=CENTS",
                   help="Override point value, e.g. --cpp chase_ur=2.0 (repeatable)")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = p.parse_args(argv)

    try:
        wallet = find_cards(load_cards(args.data_dir), args.cards.split(","))
    except UnknownCardError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not wallet:
        print("error: no cards given", file=sys.stderr)
        return 2

    merchant = None
    if args.merchant:
        merchant = resolve_merchant(args.merchant)
        if merchant is None:
            print(f"note: merchant '{args.merchant}' not in registry; ranking by category only",
                  file=sys.stderr)

    results = rank_cards(wallet, args.category, args.channel, args.amount,
                         _parse_cpp(args.cpp), merchant=merchant)

    if args.json:
        print(json.dumps(to_dict(results), indent=2))
        return 0

    top = results[0]
    where = f"{args.category} ({args.channel})"
    print(f"\nUse: {top.card.name}  -  {top.effective_return_pct:.2f}% back on {where}")
    if len(results) > 1:
        print(f"Beats {results[1].card.name} by {top.effective_return_pct - results[1].effective_return_pct:.2f} pts")
    print("\nThe math:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r.card.name}")
        for s in r.steps:
            print(f"       {s}")
        for c in r.caveats:
            print(f"       ! {c}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
