# 03_random_clans.py  — Python 3.9 compatible
import os
import sys
import time
import random
import string
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

API = "https://api.clashroyale.com/v1"


def need(k: str) -> str:
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Missing {k}. Put it in .env or export it.")
    return v


def backoff_sleep(i: int):
    time.sleep(min(60, 2 ** i))


def fetch_clans_paged(
    token: str,
    seed: str,
    limit: int = 50,
    max_pages: int = 6,
    location_id: Optional[str] = None,
    min_members: Optional[int] = None,
    max_members: Optional[int] = None,
    retries: int = 5,
):
    """
    Pull multiple pages for a given seed; returns list[(tag, name)].
    Skips pages gracefully when API returns 400 (e.g., too-short name).
    """
    headers = {"Authorization": f"Bearer {token}"}
    after = None
    out = []

    for _page in range(max_pages):
        params = {"name": seed, "limit": limit}
        if after:
            params["after"] = after
        if location_id:
            params["locationId"] = location_id
        if min_members is not None:
            params["minMembers"] = min_members
        if max_members is not None:
            params["maxMembers"] = max_members

        for i in range(retries):
            r = requests.get(f"{API}/clans", headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json() or {}
                items = data.get("items", []) or []
                for it in items:
                    tag = it.get("tag")
                    name = it.get("name")
                    if tag:
                        out.append((tag, name))
                cursors = (data.get("paging", {}) or {}).get("cursors", {}) or {}
                after = cursors.get("after")
                break
            elif r.status_code == 400:
                # common when seed is too short (<3 chars) — skip quietly
                return out
            elif r.status_code in (429, 503):
                backoff_sleep(i)
                continue
            else:
                r.raise_for_status()
        else:
            # all retries used
            break

        if not after:
            break

    return out


def random_seeds(num: int, min_len: int = 3, max_len: int = 4):
    """
    Generate alphanumeric seeds (>=3 chars to satisfy API), biased toward common substrings.
    """
    alphabet = string.ascii_lowercase + string.digits
    common = ["the", "pro", "war", "roy", "king", "clan", "legend", "mega", "star"]
    base = set(common[: min(len(common), num // 4)])
    while len(base) < num:
        L = random.randint(min_len, max_len)
        s = "".join(random.choice(alphabet) for _ in range(L))
        base.add(s)
    return list(base)

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def main():
    token = need("CR_TOKEN")

    # knobs (env vars override defaults)
    sample_n = int(os.environ.get("N_CLANS", "300"))
    num_seeds = int(os.environ.get("NUM_SEEDS", "80"))
    seed_min_len = int(os.environ.get("SEED_MIN_LEN", "3"))
    seed_max_len = int(os.environ.get("SEED_MAX_LEN", "4"))
    max_pages = int(os.environ.get("MAX_PAGES_PER_SEED", "6"))
    per_page = int(os.environ.get("LIMIT_PER_PAGE", "50"))
    out_path = os.environ.get("OUT_PATH", os.path.join(DATA_DIR, "clans.txt"))

    # optional filters
    locations_env = os.environ.get("CLAN_LOCATIONS")  # e.g. "57000000,57000007"
    locations = [x.strip() for x in locations_env.split(",")] if locations_env else [None]
    min_members_env = os.environ.get("MIN_MEMBERS")
    max_members_env = os.environ.get("MAX_MEMBERS")
    min_members = int(min_members_env) if min_members_env else None
    max_members = int(max_members_env) if max_members_env else None

    # seeds
    seeds = random_seeds(num_seeds, seed_min_len, seed_max_len)
    random.shuffle(seeds)
    random.shuffle(locations)

    tag_to_name = {}

    for seed in seeds:
        # occasionally vary member filter to diversify
        mm = min_members
        MX = max_members
        if mm is None and MX is None and random.random() < 0.25:
            mm = random.choice([0, 5, 10, 20])
            MX = random.choice([30, 40, 50])

        loc = random.choice(locations)
        try:
            results = fetch_clans_paged(
                token=token,
                seed=seed,
                limit=per_page,
                max_pages=max_pages,
                location_id=loc,
                min_members=mm,
                max_members=MX,
            )
            for tag, name in results:
                if tag not in tag_to_name:
                    tag_to_name[tag] = name
        except requests.HTTPError as e:
            # unexpected errors — keep a short log
            print(f"[warn] seed '{seed}' failed: {e}")

    tags = list(tag_to_name.keys())
    if not tags:
        sys.exit("No clans found. Check token/IP allow-list or widen seeds.")

    random.shuffle(tags)
    sample = tags[: min(sample_n, len(tags))]

    with open(out_path, "w", encoding="utf-8") as f:
        for t in sample:
            f.write(t + "\n")

    print(f"{out_path} → {len(sample)} tags (from {len(tags)} unique, seeds={len(seeds)})")


if __name__ == "__main__":
    main()
