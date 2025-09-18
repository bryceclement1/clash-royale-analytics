import os, sys, requests

API = "https://api.clashroyale.com/v1"

def need(k):
    v = os.environ.get(k)
    if not v:
        print(f"Missing {k}. Set it and re-run.", file=sys.stderr)
        sys.exit(1)
    return v

def main():
    token = need("CR_TOKEN")
    player_tag = need("CR_PLAYER")  # include leading #

    headers = {"Authorization": f"Bearer {token}"}
    tag_no_hash = player_tag.lstrip("#").upper()
    url = f"{API}/players/%23{tag_no_hash}/battlelog"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    battles = r.json()
    if not isinstance(battles, list) or not battles:
        print("No recent battles for this player.")
        return

    b = battles[0]  # look at the most recent battle
    team = (b.get("team") or [{}])[0]
    opp  = (b.get("opponent") or [{}])[0]
    tcards = team.get("cards") or []
    ocards = opp.get("cards") or []

    print(f"Game mode: {(b.get('gameMode') or {}).get('name')}")
    print(f"Player cards: {len(tcards)}  |  Opponent cards: {len(ocards)}")

    def show(side, cards):
        for c in cards[:8]:  # show up to 8 for readability
            print(f"  {side}: id={c.get('id')} name={c.get('name')} "
                  f"lvl={c.get('level')} evo={c.get('evolutionLevel')}")

    show("player", tcards)
    show("opponent", ocards)

if __name__ == "__main__":
    main()
