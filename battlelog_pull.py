import os, sys, requests, pandas as pd
from datetime import datetime, timezone

API = "https://api.clashroyale.com/v1"

def need(var):
    v = os.environ.get(var)
    if not v:
        print(f"Missing {var}. Set it and re-run.", file=sys.stderr)
        sys.exit(1)
    return v

def parse_bt(s: str):
    """Clash timestamps like 20250115T090102.000Z → ISO string."""
    if not s: return None
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return None

def main():
    token = need("CR_TOKEN")
    player_tag = need("CR_PLAYER")  # include the leading #

    headers = {"Authorization": f"Bearer {token}"}
    tag_no_hash = player_tag.lstrip("#").upper()
    url = f"{API}/players/%23{tag_no_hash}/battlelog"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data:
        print("No recent battles for this player (or bad tag).")
        sys.exit(0)

    rows = []
    for b in data:
        team = (b.get("team") or [{}])[0]
        opp  = (b.get("opponent") or [{}])[0]
        pc, oc = team.get("crowns"), opp.get("crowns")
        won = None
        if isinstance(pc, int) and isinstance(oc, int):
            won = 1 if pc > oc else (0 if pc < oc else None)

        rows.append({
            "battle_time":        parse_bt(b.get("battleTime")),
            "game_mode":          (b.get("gameMode") or {}).get("name"),
            "arena":              (b.get("arena") or {}).get("name"),
            "battle_type":        b.get("type"),
            "is_ladder_tournament": bool(b.get("isLadderTournament")),
            "player_tag":         team.get("tag"),
            "opponent_tag":       opp.get("tag"),
            "player_crowns":      pc,
            "opponent_crowns":    oc,
            "won":                won
        })

    df = pd.DataFrame(rows).sort_values("battle_time", ascending=False)

    # preview + save
    print(f"Rows: {len(df)}")
    print(df.head(10).to_string(index=False))
    df.to_csv("battlelog.csv", index=False)

if __name__ == "__main__":
    main()
