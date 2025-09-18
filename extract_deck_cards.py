import os, sys, requests, pandas as pd
from datetime import datetime, timezone

API = "https://api.clashroyale.com/v1"

def need(k):
    v = os.environ.get(k)
    if not v:
        print(f"Missing {k}. Set it and re-run.", file=sys.stderr)
        sys.exit(1)
    return v

def parse_bt(s: str):
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return None

def main():
    token = need("CR_TOKEN")
    player_tag = need("CR_PLAYER")  # include leading '#'
    headers = {"Authorization": f"Bearer {token}"}
    tag_no_hash = player_tag.lstrip("#").upper()
    url = f"{API}/players/%23{tag_no_hash}/battlelog"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    battles = r.json()
    if not isinstance(battles, list) or not battles:
        print("No recent battles for this player.")
        sys.exit(0)

    rows = []
    for b in battles:
        bt = parse_bt(b.get("battleTime",""))
        gm = (b.get("gameMode") or {}).get("name")
        arena = (b.get("arena") or {}).get("name")
        btype = b.get("type")
        is_ladder = bool(b.get("isLadderTournament"))

        for key, side in (("team","player"), ("opponent","opponent")):
            party = (b.get(key) or [{}])
            p0 = party[0] if party else {}
            cards = p0.get("cards") or []
            for idx, c in enumerate(cards, start=1):
                rows.append({
                    "battle_time": bt,
                    "game_mode": gm,
                    "arena": arena,
                    "battle_type": btype,
                    "is_ladder_tournament": is_ladder,
                    "side": side,                 # 'player' or 'opponent'
                    "deck_slot": idx,             # 1..8 normally; more for duels
                    "card_id": c.get("id"),
                    "card_name": c.get("name"),
                    "card_level": c.get("level"),
                    "evolution_level": c.get("evolutionLevel"),
                })

    df = pd.DataFrame(rows).sort_values(["battle_time","side","deck_slot"], ascending=[False, True, True])

    # preview + save
    print(f"Rows: {len(df)}  (one row per (battle, side, card))")
    print(df.head(12).to_string(index=False))
    df.to_csv("battle_cards.csv", index=False)

if __name__ == "__main__":
    main()
