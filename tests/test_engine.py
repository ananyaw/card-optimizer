"""Engine tests use synthetic fixture cards so they don't break when real card data is updated."""
from datetime import date

import pytest

from cardopt import (
    Card, EarnRule, UnknownCardError, find_cards, rank_cards, score_card, to_dict,
)
from cardopt.validate import validate_card_dict


def make_cards():
    return {
        "dine": Card(
            id="dine", name="Dining Card", issuer="X", annual_fee=100,
            currency="cash", base_rate=1,
            rules=(EarnRule("dining", 4, "any"),
                   EarnRule("groceries", 4, "any", cap_usd=25000)),
            aliases=("dc",), last_verified="2026-10-01",
        ),
        "flat": Card(
            id="flat", name="Flat Card", issuer="X", annual_fee=0,
            currency="cash", base_rate=2, last_verified="2026-10-01",
        ),
        "travel": Card(
            id="travel", name="Travel Card", issuer="X", annual_fee=500,
            currency="chase_ur", base_rate=1,
            rules=(EarnRule("hotels", 8, "portal"), EarnRule("hotels", 4, "direct")),
            last_verified="2026-10-01",
        ),
    }


TODAY = date(2026, 10, 12)


def test_bonus_category_wins():
    c = make_cards()
    res = rank_cards([c["dine"], c["flat"], c["travel"]], "dining", today=TODAY)
    assert [r.card.id for r in res] == ["dine", "flat", "travel"]
    assert res[0].effective_return_pct == pytest.approx(4.0)


def test_base_rate_fallback():
    c = make_cards()
    res = rank_cards([c["dine"], c["flat"]], "general", today=TODAY)
    assert res[0].card.id == "flat"          # 2% beats 1%
    assert res[1].rule is None


def test_channel_matters():
    c = make_cards()
    portal = score_card(c["travel"], "hotels", "portal", today=TODAY)
    direct = score_card(c["travel"], "hotels", "direct", today=TODAY)
    assert portal.rate == 8 and direct.rate == 4
    assert portal.effective_return_pct == pytest.approx(8 * 1.5)  # default chase_ur cpp


def test_cpp_override_changes_winner():
    c = make_cards()
    cards = [c["flat"], c["travel"]]
    assert rank_cards(cards, "hotels", "direct", today=TODAY)[0].card.id == "travel"  # 4*1.5=6 > 2
    res = rank_cards(cards, "hotels", "direct", cpp_map={"chase_ur": 0.4}, today=TODAY)
    assert res[0].card.id == "flat"          # 4*0.4=1.6 < 2


def test_tie_breaks_on_annual_fee_then_name():
    a = Card("a", "A Card", "X", 95, "cash", 2, last_verified="2026-10-01")
    b = Card("b", "B Card", "X", 0, "cash", 2, last_verified="2026-10-01")
    assert [r.card.id for r in rank_cards([a, b], "general", today=TODAY)] == ["b", "a"]


def test_reward_amount():
    c = make_cards()
    r = score_card(c["dine"], "dining", amount=50, today=TODAY)
    assert r.reward_usd == 2.00


def test_cap_caveat_only_when_cap_rule_applies():
    c = make_cards()
    assert any("first $25,000" in x for x in score_card(c["dine"], "groceries", today=TODAY).caveats)
    assert not any("first $" in x for x in score_card(c["dine"], "dining", today=TODAY).caveats)


def test_unverified_and_stale_caveats():
    unverified = Card("u", "U", "X", 0, "cash", 1)
    assert any("unverified" in x for x in score_card(unverified, "general", today=TODAY).caveats)
    stale = Card("s", "S", "X", 0, "cash", 1, last_verified="2025-01-01")
    assert any("may be stale" in x for x in score_card(stale, "general", today=TODAY).caveats)
    fresh = make_cards()["flat"]
    assert score_card(fresh, "general", today=TODAY).caveats == []


def test_invalid_inputs():
    c = make_cards()["flat"]
    with pytest.raises(ValueError):
        score_card(c, "spaceship")
    with pytest.raises(ValueError):
        score_card(c, "dining", "teleport")
    with pytest.raises(ValueError):
        rank_cards([], "dining")
    with pytest.raises(ValueError):
        score_card(Card("z", "Z", "X", 0, "unobtanium", 1), "dining")


def test_find_cards_alias_and_errors():
    cards = list(make_cards().values())
    assert find_cards(cards, ["DC"])[0].id == "dine"
    assert find_cards(cards, ["flat"])[0].id == "flat"
    with pytest.raises(UnknownCardError):
        find_cards(cards, ["nonexistent"])


def test_to_dict_shape():
    c = make_cards()
    out = to_dict(rank_cards([c["dine"], c["flat"]], "dining", amount=100, today=TODAY))
    assert out["winner"] == "Dining Card"
    assert out["margin_vs_runner_up_pct"] == pytest.approx(2.0)
    assert out["ranking"][0]["steps"] and out["ranking"][0]["position"] == 1


def test_validator_flags_bad_cards():
    errs, _ = validate_card_dict({"id": "x"})
    assert errs
    errs, _ = validate_card_dict({
        "id": "x", "name": "X", "issuer": "I", "annual_fee": 0, "currency": "cash",
        "base_rate": 1, "rules": [{"category": "nope", "rate": 2}],
    })
    assert any("invalid category" in e for e in errs)
