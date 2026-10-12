"""Cents-per-point assumptions. These are opinions, not facts: override per user.

Known simplification: real value depends on how you redeem and on which cards
you pool points across (e.g. Chase Freedom points are worth more alongside a
Sapphire card). v1 uses one flat number per currency. Airline/hotel values are
rough ballparks and vary widely by redemption.
"""

DEFAULT_CPP = {
    "cash": 1.0,
    "chase_ur": 1.5,
    "amex_mr": 1.5,
    "citi_typ": 1.5,
    "bilt_points": 1.5,
    "capone_miles": 1.25,
    "delta_skymiles": 1.2,
    "united_miles": 1.3,
    "aadvantage_miles": 1.4,
    "marriott_bonvoy": 0.8,
    "hilton_honors": 0.5,
}
