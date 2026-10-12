"""Co-brand (merchant-specific) rules and the merchant registry."""
from datetime import date

import pytest

from cardopt import Card, EarnRule, rank_cards, resolve_merchant, score_card
from cardopt.validate import validate_card_dict

TODAY = date(2026, 10, 12)


def cobrand():
    return Card(
        id="co", name="Store Card", issuer="X", annual_fee=0, currency="cash", base_rate=1,
        rules=(
            EarnRule("general", 5, merchant="amazon", requires="Prime membership"),
            EarnRule("dining", 3),
        ),
        last_verified="2026-10-01",
    )


def flat():
    return Card("flat", "Flat Card", "X", 0, "cash", 2, last_verified="2026-10-01")


def test_merchant_rule_applies_only_at_that_merchant():
    at = score_card(cobrand(), "general", merchant="amazon", today=TODAY)
    elsewhere = score_card(cobrand(), "general", merchant="target", today=TODAY)
    none = score_card(cobrand(), "general", today=TODAY)
    assert at.rate == 5
    assert elsewhere.rate == 1 and none.rate == 1


def test_merchant_beats_flat_card_only_at_merchant():
    cards = [cobrand(), flat()]
    assert rank_cards(cards, "general", merchant="amazon", today=TODAY)[0].card.id == "co"
    assert rank_cards(cards, "general", today=TODAY)[0].card.id == "flat"


def test_requires_becomes_caveat():
    r = score_card(cobrand(), "general", merchant="amazon", today=TODAY)
    assert any("Prime membership" in c for c in r.caveats)
    assert not score_card(cobrand(), "dining", today=TODAY).caveats  # no condition on dining rule


def test_highest_matching_rule_wins_across_merchant_and_category():
    card = Card("c", "C", "X", 0, "cash", 1, rules=(
        EarnRule("dining", 3),
        EarnRule("general", 2, merchant="whole_foods"),
    ), last_verified="2026-10-01")
    assert score_card(card, "dining", merchant="whole_foods", today=TODAY).rate == 3


def test_general_non_merchant_rule_is_catch_all_bonus():
    card = Card("a", "A", "X", 0, "cash", 1, rules=(
        EarnRule("general", 2, requires="paying with Apple Pay"),
    ), last_verified="2026-10-01")
    for cat in ("dining", "gas", "general"):
        r = score_card(card, cat, today=TODAY)
        assert r.rate == 2 and any("Apple Pay" in c for c in r.caveats)


def test_merchant_case_insensitive():
    assert score_card(cobrand(), "general", merchant="AMAZON", today=TODAY).rate == 5


@pytest.mark.parametrize("text,expected", [
    ("https://www.amazon.com/checkout", "amazon"),
    ("smile.amazon.com", "amazon"),
    ("amazon", "amazon"),
    ("Whole Foods", "whole_foods"),
    ("costco.com/cart", "costco"),
    ("notamazon.com", None),
    ("", None),
    ("some random shop", None),
])
def test_resolve_merchant(text, expected):
    assert resolve_merchant(text) == expected


def test_validator_checks_merchant_ids_and_sources():
    base = {"id": "x", "name": "X", "issuer": "I", "annual_fee": 0, "currency": "cash", "base_rate": 1}
    errs, _ = validate_card_dict({**base, "rules": [{"merchant": "nowhere", "rate": 5}]})
    assert any("unknown merchant" in e for e in errs)
    errs, warns = validate_card_dict({**base, "rules": [{"merchant": "amazon", "rate": 5}]})
    assert errs == [] and any("no source_url" in w for w in warns)
    errs, _ = validate_card_dict({**base, "rules": [{"rate": 5}]})
    assert any("category or a merchant" in e for e in errs)
