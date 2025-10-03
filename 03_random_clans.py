import os
import sys
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()
API = "https://api.clashroyale.com/v1"

def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Put it in .env or export it.")
    return v

def fetch_clans(token: str, seed: str, limit: int = 50, retries: int = 5):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"name": seed, "limit": limit}
    for i in range(retries):
        r = requests.get(f"{API}/clans", headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            items = r.json().get("items", [])
            return [(it.get("tag"), it.get("name")) for it in items if it.get("tag")]
        if r.status_code in (429, 503):
            time.sleep(min(60, 2**i))
            continue
        r.raise_for_status()
    return []

def main():
    token = need("CR_TOKEN")
    seeds_env = os.environ.get("CLAN_SEEDS")
    if seeds_env:
        seeds = [s.strip() for s in seeds_env.split(",") if s.strip()]
    else:
        seeds = [
            "the","pro","war","king","queen","royal","storm","fire","abc","xyz",
            "dark","elite","knight","ninja","dragon","clan","mega","god","nova","star"
        ]
    sample_n = int(os.environ.get("N_CLANS", "60"))

    tag_to_name = {}
    for s in seeds:
        try:
            for t, name in fetch_clans(token, s, limit=50):
                if t and t not in tag_to_name:
                    tag_to_name[t] = name
        except Exception as e:
            print(f"[warn] seed '{s}' failed: {e}")

    tags = list(tag_to_name.keys())
    if not tags:
        sys.exit("No clans found. Try different seeds or check token/IP allow-list.")

    random.shuffle(tags)
    sample = tags[: min(sample_n, len(tags))]

    with open("clans.txt", "w") as f:
        for t in sample:
            f.write(t + "\n")

    print(f"clans.txt → {len(sample)} tags (from {len(tags)} unique)")

if __name__ == "__main__":
    main()
