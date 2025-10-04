# 02_load_cards_csv.py  (rename your old 02_load_cards.py to this)
import os
import sys
import csv
import requests
from dotenv import load_dotenv

load_dotenv()
API = "https://api.clashroyale.com/v1"

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Set it in .env or export it.")
    return v

def fetch_cards(token: str):
    r = requests.get(
        f"{API}/cards",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    out = []
    for it in items:
        icon = (it.get("iconUrls") or {})
        out.append({
            "id": it.get("id"),
            "name": it.get("name"),
            "max_level": it.get("maxLevel"),
            "elixir": it.get("elixirCost") or it.get("elixir"),
            "rarity": it.get("rarity"),
            "icon_url": icon.get("medium") or icon.get("large") or icon.get("evolutionMedium"),
            "is_champion": bool(it.get("isChampion") or (str(it.get("rarity","")).lower() == "champion")),
            "is_evolution": bool(it.get("isEvolution")),
        })
    return [r for r in out if r["id"] is not None]

def main():
    token = need("CR_TOKEN")
    rows = fetch_cards(token)
    print(f"Fetched {len(rows)} cards")

    with open(os.path.join(DATA_DIR, "cards.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id","name","max_level","elixir","rarity","icon_url","is_champion","is_evolution"]
        )
        w.writeheader()
        w.writerows(rows)

    print("✅ cards.csv written")

if __name__ == "__main__":
    main()
