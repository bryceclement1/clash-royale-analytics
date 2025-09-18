import os
import sys
import requests
import pandas as pd

API = "https://api.clashroyale.com/v1"

def require_token():
    tok = os.environ.get("CR_TOKEN")
    if not tok:
        print("Missing CR_TOKEN. In this terminal, run:\n  export CR_TOKEN='YOUR_TOKEN_HERE'\nthen re-run:  python cards_pull.py", file=sys.stderr)
        sys.exit(1)
    return tok

def col(df, name):
    # safe column getter (returns Series of Nones if missing)
    return df[name] if name in df.columns else pd.Series([None] * len(df))

def main():
    token = require_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/cards", headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    if not items:
        print("No items returned. Check token/IP allow-list.", file=sys.stderr)
        sys.exit(2)

    raw = pd.json_normalize(items)

    # Clean fields
    elixir = col(raw, "elixirCost")
    if "elixir" in raw.columns:
        elixir = elixir.fillna(raw["elixir"])
    icon_url = col(raw, "iconUrls.medium")
    icon_url = icon_url.fillna(col(raw, "iconUrls.large")).fillna(col(raw, "iconUrls.evolutionMedium"))

    out = pd.DataFrame({
        "card_id": col(raw, "id").astype("Int64"),
        "name": col(raw, "name"),
        "max_level": col(raw, "maxLevel").astype("Int64"),
        "elixir": elixir.astype("Int64"),
        "rarity": col(raw, "rarity"),
        "icon_url": icon_url,
        "is_champion": col(raw, "isChampion").fillna(False).astype("boolean"),
        "is_evolution": col(raw, "isEvolution").fillna(False).astype("boolean"),
    })

    # Show a quick preview
    out.to_csv("cards.csv", index=False)
    print(f"Rows: {len(out)}, Columns: {len(out.columns)}")
    print(out.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
