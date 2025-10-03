import os
import sys
import csv
from dotenv import load_dotenv

load_dotenv()

DSN = os.environ.get("PG_DSN")
if not DSN:
    sys.exit("PG_DSN missing. Put it in .env or export it.")

BATCH = int(os.environ.get("BATCH_SIZE", "5000"))

SQL_BATTLES = """
INSERT INTO fact_battles
(battle_id, player_tag, opponent_tag, battle_time, mode, arena, player_crowns, opponent_crowns, is_ladder_tournament, battle_type)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (battle_id) DO NOTHING;
"""

SQL_CARDS = """
INSERT INTO battle_cards
(battle_id, side, card_id, card_level, evolution_level)
VALUES (%s,%s,%s,%s,%s)
ON CONFLICT (battle_id, side, card_id) DO NOTHING;
"""

def to_int(x):
    try:
        return int(x) if x not in ("", None) else None
    except Exception:
        return None

def to_bool(x):
    s = str(x).strip().lower()
    if s in ("true","t","1","yes","y"): return True
    if s in ("false","f","0","no","n"): return False
    return None

def connect(dsn):
    try:
        import psycopg as pg
        return "pg3", pg.connect(dsn)
    except ModuleNotFoundError:
        import psycopg2 as pg2
        return "pg2", pg2.connect(dsn)

def main():
    if not (os.path.exists("battles_raw.csv") and os.path.exists("battle_cards_raw.csv")):
        sys.exit("Missing CSVs. Run 05_pull_battles_for_players.py first.")

    driver, conn = connect(DSN)
    with conn:
        with conn.cursor() as cur:
            # battles
            total_b = 0
            batch = []
            with open("battles_raw.csv") as f:
                r = csv.DictReader(f)
                for row in r:
                    batch.append((
                        row["battle_id"], row.get("player_tag"), row.get("opponent_tag"),
                        row.get("battle_time"), row.get("mode"), row.get("arena"),
                        to_int(row.get("player_crowns")), to_int(row.get("opponent_crowns")),
                        to_bool(row.get("is_ladder_tournament")), row.get("battle_type"),
                    ))
                    if len(batch) >= BATCH:
                        cur.executemany(SQL_BATTLES, batch); total_b += len(batch); batch.clear()
                if batch:
                    cur.executemany(SQL_BATTLES, batch); total_b += len(batch)

            # battle_cards
            total_c = 0
            batch = []
            with open("battle_cards_raw.csv") as f:
                r = csv.DictReader(f)
                for row in r:
                    batch.append((
                        row["battle_id"], row.get("side"),
                        to_int(row.get("card_id")), to_int(row.get("card_level")), to_int(row.get("evolution_level")),
                    ))
                    if len(batch) >= BATCH:
                        cur.executemany(SQL_CARDS, batch); total_c += len(batch); batch.clear()
                if batch:
                    cur.executemany(SQL_CARDS, batch); total_c += len(batch)

    print(f"Inserted (dedup-safe) {total_b} battles and {total_c} card rows.")

if __name__ == "__main__":
    main()
