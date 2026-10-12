"""Sanity checks on the real card files shipped in data/cards."""
import json

from cardopt import load_cards, rank_cards
from cardopt.loader import DEFAULT_DATA_DIR
from cardopt.validate import validate_card_dict


def test_all_card_files_pass_schema():
    files = sorted(DEFAULT_DATA_DIR.glob("*.json"))
    assert len(files) >= 5
    for p in files:
        errors, _ = validate_card_dict(json.loads(p.read_text(encoding="utf-8")))
        assert errors == [], f"{p.name}: {errors}"


def test_unique_ids_and_every_card_rankable():
    cards = load_cards()
    assert len({c.id for c in cards}) == len(cards)
    from cardopt.models import CATEGORIES
    for cat in CATEGORIES:
        assert len(rank_cards(cards, cat, "direct")) == len(cards)
