import os
import sys
import time
import random
import requests
import hashlib
import csv
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API = "https://api.clashroyale.com/v1"

def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Put it in .env or export it.")
    return v

def parse_bt(s: str):
    if not s:
        return None
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return None

def make_battle_id(player_tag, bt_iso, mode, opponent_tag):
    base = f"{player_tag}|{bt_iso}|{mode or ''}|{opponent_tag or ''}"
    return hashlib.md5(base.encode()).hexdigest()

def fetch_log(token: str, tag: str, retries: int = 5):
    headers = {"Authorization": f"Bearer {token}"}
    t = tag.lstrip("#").upper()
    url = f"{API}/players/%23{t}/battlelog"
    for i in range(retries):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 503):
            time.sleep(min(60, 2**i))
            continue
        r.raise_for_status()
    return []

def main():
    token = need("CR_TOKEN")

    if not os.path.exists("players.txt"):
        sys.exit("players.txt not found. Run 04_random_players_from_clans.py first.")
    with open("players.txt") as f:
        tags = [line.strip() for line in f if line.strip()]

    random.shuffle(tags)
    n_players = int(os.environ.get("N_PLAYERS", "400"))
    sleep_ms = int(os.environ.get("SLEEP_MS", "250"))

    battles_cols = [
        "battle_id","player_tag","opponent_tag","battle_time","mode","arena",
        "player_crowns","opponent_crowns","is_ladder_tournament","battle_type","won"
    ]
    cards_cols = ["battle_id","side","card_id","card_level","evolution_level"]

    tb = tc = 0
    with open("battles_raw.csv", "w", newline="") as fb, open("battle_cards_raw.csv", "w", newline="") as fc:
        bw = csv.DictWriter(fb, fieldnames=battles_cols); bw.writeheader()
        cw = csv.DictWriter(fc, fieldnames=cards_cols);   cw.writeheader()

        for i, tag in enumerate(tags[:n_players], start=1):
            try:
                data = fetch_log(token, tag)
                if not isinstance(data, list):
                    continue
                for b in data:
                    bt_iso = parse_bt(b.get("battleTime"))
                    team = (b.get("team") or [{}])[0]
                    opp  = (b.get("opponent") or [{}])[0]
                    pc, oc = team.get("crowns"), opp.get("crowns")
                    won = None
                    if isinstance(pc, int) and isinstance(oc, int):
                        won = 1 if pc > oc else (0 if pc < oc else None)

                    row = {
                        "battle_id": make_battle_id(team.get("tag"), bt_iso, (b.get("gameMode") or {}).get("name"), opp.get("tag")),
                        "player_tag": team.get("tag"),
                        "opponent_tag": opp.get("tag"),
                        "battle_time": bt_iso,
                        "mode": (b.get("gameMode") or {}).get("name"),
                        "arena": (b.get("arena") or {}).get("name"),
                        "player_crowns": pc,
                        "opponent_crowns": oc,
                        "is_ladder_tournament": bool(b.get("isLadderTournament")),
                        "battle_type": b.get("type"),
                        "won": won
                    }
                    bw.writerow(row)
                    tb += 1

                    # explode cards for both sides
                    for key, side in (("team", "player"), ("opponent", "opponent")):
                        p0 = (b.get(key) or [{}])[0]
                        for c in (p0.get("cards") or []):
                            cid = c.get("id")
                            if cid is None:
                                continue
                            cw.writerow({
                                "battle_id": row["battle_id"],
                                "side": side,
                                "card_id": cid,
                                "card_level": c.get("level"),
                                "evolution_level": c.get("evolutionLevel"),
                            })
                            tc += 1

                if i % 50 == 0:
                    print(f"...{i} players processed")
                time.sleep(sleep_ms / 1000.0)

            except Exception as e:
                print("[warn]", tag, e)

    print(f"battles_raw.csv: {tb} rows, battle_cards_raw.csv: {tc} rows")

if __name__ == "__main__":
    main()
