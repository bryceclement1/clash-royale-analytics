import os
import sys
from dotenv import load_dotenv

load_dotenv()

DSN = os.environ.get("PG_DSN")
if not DSN:
    sys.exit("PG_DSN missing. Put it in .env or export it.")

SQL = """
DO $$
DECLARE rows_deleted integer := 1;
BEGIN
  WHILE rows_deleted > 0 LOOP
    DELETE FROM fact_battles
    WHERE ctid IN (
      SELECT ctid FROM fact_battles
      WHERE battle_time < now() - interval '90 days'
      LIMIT 10000
    );
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    RAISE NOTICE 'deleted % rows', rows_deleted;
  END LOOP;
END$$;

VACUUM ANALYZE fact_battles;
VACUUM ANALYZE battle_cards;
"""

def run():
    try:
        import psycopg as pg
        with pg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute(SQL)
            conn.commit()
    except ModuleNotFoundError:
        import psycopg2 as pg2
        with pg2.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute(SQL)
            conn.commit()

run()
print("✅ retention applied (kept ≤ 90 days)")
