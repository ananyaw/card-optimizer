"""Inject the static card list from data/cards/*.json into extension/onboarding.html.

Run after adding or editing cards:
    python scripts/build_extension_data.py
    python scripts/build_extension_data.py --standalone   # also write one-file preview
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "data" / "cards"
EXT = ROOT / "extension"
HTML = EXT / "onboarding.html"

START, END = "<!--CARD_DATA_START-->", "<!--CARD_DATA_END-->"


def card_list():
    cards = []
    for p in sorted(CARDS_DIR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        cards.append({
            "id": d["id"], "name": d["name"], "issuer": d["issuer"],
            "aliases": d.get("aliases", []),
        })
    cards.sort(key=lambda c: (c["issuer"].lower(), c["name"].lower()))
    return cards


def inject(html: str, cards) -> str:
    payload = json.dumps(cards, indent=2).replace("</", "<\\/")
    block = f'{START}<script id="card-data" type="application/json">{payload}</script>{END}'
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(html):
        raise SystemExit("Card data markers not found in onboarding.html")
    return pattern.sub(lambda _: block, html)


def main():
    cards = card_list()
    html = inject(HTML.read_text(encoding="utf-8"), cards)
    HTML.write_text(html, encoding="utf-8")
    print(f"Injected {len(cards)} cards into {HTML.relative_to(ROOT)}")

    if "--standalone" in sys.argv:
        css = (EXT / "onboarding.css").read_text(encoding="utf-8")
        js = (EXT / "onboarding.js").read_text(encoding="utf-8")
        solo = html.replace('<link rel="stylesheet" href="onboarding.css">', f"<style>\n{css}\n</style>")
        solo = solo.replace('<script src="onboarding.js"></script>', f"<script>\n{js}\n</script>")
        out = EXT / "onboarding.standalone.html"
        out.write_text(solo, encoding="utf-8")
        print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
