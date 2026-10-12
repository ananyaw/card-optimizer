from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List

from .models import Card, EarnRule

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cards"


class UnknownCardError(ValueError):
    pass


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def card_from_dict(d: dict) -> Card:
    rules = tuple(
        EarnRule(
            category=r.get("category", "general"),
            rate=float(r["rate"]),
            channel=r.get("channel", "any"),
            cap_usd=r.get("cap_usd"),
            note=r.get("note", ""),
            merchant=r.get("merchant", ""),
            requires=r.get("requires", ""),
            source_url=r.get("source_url", ""),
            source_quote=r.get("source_quote", ""),
        )
        for r in d.get("rules", [])
    )
    return Card(
        id=d["id"],
        name=d["name"],
        issuer=d["issuer"],
        annual_fee=float(d["annual_fee"]),
        currency=d["currency"],
        base_rate=float(d["base_rate"]),
        rules=rules,
        aliases=tuple(d.get("aliases", [])),
        credits=tuple(d.get("credits", [])),
        last_verified=d.get("last_verified"),
        notes=d.get("notes", ""),
        terms_url=d.get("terms_url", ""),
    )


def load_cards(data_dir: Path = DEFAULT_DATA_DIR) -> List[Card]:
    data_dir = Path(data_dir)
    return [
        card_from_dict(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(data_dir.glob("*.json"))
    ]


def find_cards(all_cards: Iterable[Card], names: Iterable[str]) -> List[Card]:
    """Resolve user-typed names ("csr", "amex gold") to cards.

    Matches id, full name, or alias (case/punctuation-insensitive), then falls
    back to a unique substring match. Raises UnknownCardError with suggestions.
    """
    all_cards = list(all_cards)
    found: List[Card] = []
    for raw in names:
        key = _norm(raw)
        if not key:
            continue
        exact = [
            c for c in all_cards
            if key in {_norm(c.id), _norm(c.name), *(_norm(a) for a in c.aliases)}
        ]
        if len(exact) == 1:
            found.append(exact[0])
            continue
        partial = [
            c for c in all_cards
            if key in _norm(c.name) or any(key in _norm(a) for a in c.aliases)
        ]
        if len(partial) == 1:
            found.append(partial[0])
            continue
        options = ", ".join(c.name for c in (partial or all_cards))
        raise UnknownCardError(f"Could not resolve card '{raw}'. Options: {options}")
    return found
