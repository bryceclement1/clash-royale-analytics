import os
import sys
import time
import random
import requests
import csv
from dotenv import load_dotenv

load_dotenv()
API = "https://api.clashroyale.com/v1"

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

CLANS_PATH   = os.path.join(DATA_DIR, "clans.txt")
PLAYERS_TXT  = os.path.join(DATA_DIR, "players.txt")
PLAYERS_CSV  = os.path.join(DATA_DIR, "players.csv")

def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Put it in .env or export it.")
    return v

def clan_members(token: str, clan_tag: str, retries: int = 5):
    headers = {"Authorization": f"Bearer {token}"}
    t = clan_tag.lstrip("#").upper()
    url = f"{API}/clans/%23{t}"
    for i in range(retries):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            j = r.json()
            members = j.get("memberList") or []
            out = []
            for m in members:
                tag = m.get("tag")
                if not tag:
                    continue
                out.append({
                    "tag": tag,
                    "name": m.get("name"),
                    "trophies": m.get("trophies"),
                    "clan_tag": j.get("tag"),
                    "clan_name": j.get("name"),
                })
            return out
        if r.status_code in (429, 503):
            time.sleep(min(60, 2**i))
            continue
        r.raise_for_status()
    return []

def main():
    token = need("CR_TOKEN")
    if not os.path.exists(CLANS_PATH):
        sys.exit("clans.txt not found. Run 02_random_clans.py first.")

    with open(CLANS_PATH) as f:
        clan_tags = [line.strip() for line in f if line.strip()]

    all_players = []
    seen = set()
    for ct in clan_tags:
        try:
            for p in clan_members(token, ct):
                if p["tag"] not in seen:
                    seen.add(p["tag"])
                    all_players.append(p)
        except Exception as e:
            print(f"[warn] could not fetch members for {ct}: {e}")

    if not all_players:
        sys.exit("No players found. Try increasing N_CLANS or different seeds.")

    random.shuffle(all_players)
    sample_n = int(os.environ.get("N_PLAYERS", "400"))
    sample = all_players[: min(sample_n, len(all_players))]

    with open(PLAYERS_TXT, "w") as f:
        for p in sample:
            f.write(p["tag"] + "\n")

    with open(PLAYERS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "name", "trophies", "clan_tag", "clan_name"])
        w.writeheader()
        w.writerows(sample)

    print(f"players.txt → {len(sample)} tags (from {len(all_players)} unique)")

if __name__ == "__main__":
    main()
