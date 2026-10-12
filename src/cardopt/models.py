from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

# Purchase categories the engine understands. The classification agent (Phase 3)
# maps free-text purchases onto these.
CATEGORIES = (
    "dining", "groceries", "flights", "hotels",
    "car_rental", "gas", "drugstore", "general",
)

# direct = paid straight to the merchant; portal = booked via the issuer's travel portal
CHANNELS = ("direct", "portal")


@dataclass(frozen=True)
class EarnRule:
    category: str                    # "general" for merchant-only rules
    rate: float                      # points/miles/% per $1 (e.g. 4 = 4x)
    channel: str = "any"             # any | direct | portal
    cap_usd: Optional[float] = None  # annual spend cap for this rate, if any
    note: str = ""
    merchant: str = ""               # merchant id (see data/merchants.json); rule applies only there
    requires: str = ""               # condition the user must meet, e.g. "Prime membership"
    source_url: str = ""             # where this rule was read (for the auditor)
    source_quote: str = ""           # exact supporting text from that page


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    issuer: str
    annual_fee: float
    currency: str                    # key into the valuations map (e.g. chase_ur)
    base_rate: float                 # earn rate on everything else
    rules: Tuple[EarnRule, ...] = ()
    aliases: Tuple[str, ...] = ()
    credits: Tuple[dict, ...] = ()   # not used by the engine yet (Phase 4 nudges)
    last_verified: Optional[str] = None  # ISO date; None = unverified
    notes: str = ""
    terms_url: str = ""              # issuer page the auditor should check


@dataclass
class CardResult:
    card: Card
    rate: float
    cpp: float                       # cents per point/mile
    effective_return_pct: float      # rate * cpp
    reward_usd: Optional[float]
    rule: Optional[EarnRule]         # None = base rate applied
    steps: list = field(default_factory=list)    # human-readable math
    caveats: list = field(default_factory=list)
