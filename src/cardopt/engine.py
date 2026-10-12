"""Deterministic ranking engine. No LLM here: the math must be predictable.

The classification agent (Phase 3) decides category + channel (+ merchant); this
module turns those into a ranked list with a human-readable breakdown.
"""
from __future__ import annotations

from datetime import date
from typing import List, Mapping, Optional, Sequence

from .models import CATEGORIES, CHANNELS, Card, CardResult, EarnRule
from .valuations import DEFAULT_CPP

STALE_DAYS = 180


def rule_matches(r: EarnRule, category: str, channel: str, merchant: Optional[str]) -> bool:
    """Merchant rules apply only at that merchant; other rules match category + channel.

    A non-merchant rule with category "general" is a catch-all bonus (e.g. Apple Card's
    2% with Apple Pay) and applies to every category.
    """
    if r.merchant:
        return merchant is not None and r.merchant == merchant
    return r.category in (category, "general") and r.channel in ("any", channel)


def best_rule(card: Card, category: str, channel: str,
              merchant: Optional[str] = None) -> Optional[EarnRule]:
    """Highest-rate rule that matches, or None."""
    candidates = [r for r in card.rules if rule_matches(r, category, channel, merchant)]
    return max(candidates, key=lambda r: r.rate, default=None)


def score_card(
    card: Card,
    category: str,
    channel: str = "direct",
    amount: Optional[float] = None,
    cpp_map: Optional[Mapping[str, float]] = None,
    today: Optional[date] = None,
    merchant: Optional[str] = None,
) -> CardResult:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category '{category}'. Valid: {', '.join(CATEGORIES)}")
    if channel not in CHANNELS:
        raise ValueError(f"Unknown channel '{channel}'. Valid: {', '.join(CHANNELS)}")

    cpp_map = {**DEFAULT_CPP, **(cpp_map or {})}
    if card.currency not in cpp_map:
        raise ValueError(f"No valuation for currency '{card.currency}' ({card.name})")
    cpp = cpp_map[card.currency]
    today = today or date.today()
    merchant = merchant.lower() if merchant else None

    rule = best_rule(card, category, channel, merchant)
    if rule is not None and rule.rate > card.base_rate:
        rate = rule.rate
        if rule.merchant:
            why = f"{rate:g}x at {rule.merchant}"
        else:
            why = f"{rate:g}x on {category} ({channel})"
        if rule.note:
            why += f" - {rule.note}"
    else:
        rule = None
        rate = card.base_rate
        why = f"no bonus category matched; base rate {rate:g}x"

    pct = rate * cpp
    reward_usd = round(amount * pct / 100, 2) if amount is not None else None

    steps = [
        f"Rule: {why}",
        f"Value: {rate:g}x * {cpp:g} cents/pt = {pct:.2f}% back",
    ]
    if reward_usd is not None:
        steps.append(f"On ${amount:,.2f}: ${reward_usd:,.2f} in rewards")
    if card.annual_fee:
        steps.append(f"Annual fee ${card.annual_fee:,.0f} (not included in per-purchase return)")

    caveats: List[str] = []
    if rule is not None and rule.requires:
        caveats.append(f"Assumes you have: {rule.requires}.")
    if rule is not None and rule.cap_usd:
        caveats.append(
            f"Bonus rate applies to the first ${rule.cap_usd:,.0f}/yr of spend; "
            f"beyond that it earns {card.base_rate:g}x."
        )
    if card.last_verified is None:
        caveats.append("Card terms unverified - check the issuer site.")
    else:
        age = (today - date.fromisoformat(card.last_verified)).days
        if age > STALE_DAYS:
            caveats.append(f"Card terms last verified {age} days ago - may be stale.")

    return CardResult(
        card=card, rate=rate, cpp=cpp, effective_return_pct=pct,
        reward_usd=reward_usd, rule=rule, steps=steps, caveats=caveats,
    )


def rank_cards(
    cards: Sequence[Card],
    category: str,
    channel: str = "direct",
    amount: Optional[float] = None,
    cpp_map: Optional[Mapping[str, float]] = None,
    today: Optional[date] = None,
    merchant: Optional[str] = None,
) -> List[CardResult]:
    """Best first. Ties break on lower annual fee, then name (stable, explainable)."""
    if not cards:
        raise ValueError("rank_cards needs at least one card")
    results = [score_card(c, category, channel, amount, cpp_map, today, merchant) for c in cards]
    results.sort(key=lambda r: (-round(r.effective_return_pct, 6), r.card.annual_fee, r.card.name))
    return results


def to_dict(results: Sequence[CardResult]) -> dict:
    """JSON-friendly output. This is what the extension's deep-dive panel will render."""
    ranking = []
    for i, r in enumerate(results):
        ranking.append({
            "position": i + 1,
            "card": r.card.name,
            "rate": r.rate,
            "cents_per_point": r.cpp,
            "effective_return_pct": round(r.effective_return_pct, 4),
            "reward_usd": r.reward_usd,
            "bonus_rule_applied": r.rule is not None,
            "requires": r.rule.requires if r.rule else "",
            "source_url": r.rule.source_url if r.rule else "",
            "steps": r.steps,
            "caveats": r.caveats,
        })
    margin = None
    if len(results) > 1:
        margin = round(results[0].effective_return_pct - results[1].effective_return_pct, 4)
    return {
        "winner": results[0].card.name,
        "margin_vs_runner_up_pct": margin,
        "ranking": ranking,
    }
