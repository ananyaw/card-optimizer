"""Merchant registry: maps domains / names to stable merchant ids.

The extension can resolve a checkout domain deterministically (no AI needed);
the classification agent (Phase 3) only has to infer a merchant when the domain
is ambiguous.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

DEFAULT_MERCHANTS = Path(__file__).resolve().parents[2] / "data" / "merchants.json"


def load_merchants(path: Path = DEFAULT_MERCHANTS) -> List[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _host(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"^[a-z]+://", "", t)
    t = t.split("/")[0].split("?")[0].split(":")[0]
    return t[4:] if t.startswith("www.") else t


def resolve_merchant(text: str, merchants: Optional[List[dict]] = None) -> Optional[str]:
    """Return a merchant id for a URL, domain, name, or alias; None if unknown."""
    if not text or not text.strip():
        return None
    merchants = merchants if merchants is not None else load_merchants()

    host = _host(text)
    for m in merchants:
        for d in m.get("domains", []):
            if host == d or host.endswith("." + d):
                return m["id"]

    key = _norm(text)
    for m in merchants:
        names = [m["id"], m["name"], *m.get("aliases", [])]
        if key in {_norm(n) for n in names}:
            return m["id"]
    return None
