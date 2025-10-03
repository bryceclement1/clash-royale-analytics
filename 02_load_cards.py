# 02_load_cards.py
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.clashroyale.com/v1"

UPSERT = """
INSERT INTO dim_cards (id,name,max_level,elixir,rarity,icon_url,is_champion,is_evolution)
VALUES (%(id)s,%(name)s,%(max_level)s,%(elixir)s,%(rarity)s,%(icon_url)s,%(is_champion)s,%(is_evolution)s)
ON CONFLICT (id) DO UPDATE SET
  name=EXCLUDED.name,
  max_level=EXCLUDED.max_level,
  elixir=EXCLUDED.elixir,
  rarity=EXCLUDED.rarity,
  icon_url=EXCLUDED.icon_url,
  is_champion=EXCLUDED.is_champion,
  is_evolution=EXCLUDED.is_evolution;
"""

def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Set it in .env or export it in your shell.")
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
    CR_TOKEN = need("CR_TOKEN")
    PG_DSN   = need("PG_DSN")

    rows = fetch_cards(CR_TOKEN)
    print(f"Fetched {len(rows)} cards")

    try:
        import psycopg as pg  # psycopg3
        with pg.connect(PG_DSN) as conn, conn.cursor() as cur:
            cur.executemany(UPSERT, rows)
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM dim_cards")
            print("dim_cards:", cur.fetchone()[0])
    except ModuleNotFoundError:
        import psycopg2 as pg2  # fallback
        with pg2.connect(PG_DSN) as conn, conn.cursor() as cur:
            cur.executemany(UPSERT, rows)
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM dim_cards")
            print("dim_cards:", cur.fetchone()[0])

if __name__ == "__main__":
    main()
