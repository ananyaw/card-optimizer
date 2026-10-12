"""Schema check for card files. Run: python -m cardopt.validate [data_dir]"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from .loader import DEFAULT_DATA_DIR
from .merchants import load_merchants
from .models import CATEGORIES
from .valuations import DEFAULT_CPP

REQUIRED = ("id", "name", "issuer", "annual_fee", "currency", "base_rate")
CHANNEL_VALUES = ("any", "direct", "portal")


def validate_card_dict(d: dict, merchant_ids=None) -> tuple:
    """Return (errors, warnings) for one card dict."""
    errors, warnings = [], []
    for k in REQUIRED:
        if k not in d:
            errors.append(f"missing required field '{k}'")
    if errors:
        return errors, warnings

    if merchant_ids is None:
        merchant_ids = {m["id"] for m in load_merchants()}

    if d["currency"] not in DEFAULT_CPP:
        errors.append(f"unknown currency '{d['currency']}' (known: {', '.join(DEFAULT_CPP)})")
    br, fee = d["base_rate"], d["annual_fee"]
    if not isinstance(br, (int, float)) or isinstance(br, bool) or br <= 0:
        errors.append("base_rate must be a number > 0")
    if not isinstance(fee, (int, float)) or isinstance(fee, bool) or fee < 0:
        errors.append("annual_fee must be a number >= 0 (got %r)" % (fee,))

    rules = d.get("rules", [])
    for i, r in enumerate(rules):
        where = f"rules[{i}]"
        merchant = r.get("merchant")
        category = r.get("category")
        if merchant:
            if merchant not in merchant_ids:
                errors.append(f"{where}: unknown merchant '{merchant}' (add it to data/merchants.json)")
            if category is not None and category not in CATEGORIES:
                errors.append(f"{where}: invalid category '{category}'")
        elif category is None:
            errors.append(f"{where}: needs a category or a merchant")
        elif category not in CATEGORIES:
            errors.append(f"{where}: invalid category '{category}'")
        if r.get("channel", "any") not in CHANNEL_VALUES:
            errors.append(f"{where}: invalid channel '{r.get('channel')}'")
        if not isinstance(r.get("rate"), (int, float)) or r["rate"] <= 0:
            errors.append(f"{where}: rate must be a positive number")

    unsourced = sum(1 for r in rules if not r.get("source_url"))
    if unsourced:
        warnings.append(f"{unsourced} of {len(rules)} rules have no source_url")

    lv = d.get("last_verified")
    if lv is None:
        warnings.append("terms unverified (last_verified is null)")
    else:
        try:
            date.fromisoformat(lv)
        except ValueError:
            errors.append(f"last_verified '{lv}' is not an ISO date")
    return errors, warnings


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    data_dir = Path(argv[0]) if argv else DEFAULT_DATA_DIR
    files = sorted(data_dir.glob("*.json"))
    if not files:
        print(f"No card files in {data_dir}")
        return 1
    bad = 0
    for p in files:
        try:
            errs, warns = validate_card_dict(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            errs, warns = [f"invalid JSON: {e}"], []
        status = "FAIL" if errs else "ok"
        print(f"[{status}] {p.name}")
        for e in errs:
            print(f"    error: {e}")
        for w in warns:
            print(f"    warn:  {w}")
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
