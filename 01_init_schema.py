import os, sys
from dotenv import load_dotenv; load_dotenv()

DDL = [
    """
    CREATE TABLE IF NOT EXISTS dim_cards (
      id BIGINT PRIMARY KEY,
      name TEXT,
      max_level SMALLINT,
      elixir SMALLINT,
      rarity TEXT,
      icon_url TEXT,
      is_champion BOOLEAN,
      is_evolution BOOLEAN
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_battles (
      battle_id CHAR(32) PRIMARY KEY,
      player_tag TEXT NOT NULL,
      opponent_tag TEXT,
      battle_time TIMESTAMPTZ NOT NULL,
      mode TEXT,
      arena TEXT,
      player_crowns SMALLINT,
      opponent_crowns SMALLINT,
      is_ladder_tournament BOOLEAN,
      battle_type TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_battles_player_time ON fact_battles (player_tag, battle_time DESC);",
    "CREATE INDEX IF NOT EXISTS idx_battles_time ON fact_battles (battle_time DESC);",
    """
    CREATE TABLE IF NOT EXISTS battle_cards (
      battle_id CHAR(32) NOT NULL,
      side TEXT NOT NULL CHECK (side IN ('player','opponent')),
      card_id BIGINT NOT NULL,
      card_level SMALLINT,
      evolution_level SMALLINT,
      PRIMARY KEY (battle_id, side, card_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_bc_card ON battle_cards (card_id);",
    "CREATE INDEX IF NOT EXISTS idx_bc_battle ON battle_cards (battle_id);",
    # FK for cascade retention
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_bc_battle') THEN
        ALTER TABLE battle_cards
        ADD CONSTRAINT fk_bc_battle
        FOREIGN KEY (battle_id) REFERENCES fact_battles(battle_id)
        ON DELETE CASCADE;
      END IF;
    END$$;
    """
]

dsn = os.environ.get("PG_DSN") or sys.exit("PG_DSN missing")
def run(sqls):
    try:
        import psycopg as pg
        with pg.connect(dsn) as conn, conn.cursor() as cur:
            for s in sqls: cur.execute(s)
            conn.commit()
    except ModuleNotFoundError:
        import psycopg2 as pg2
        with pg2.connect(dsn) as conn, conn.cursor() as cur:
            for s in sqls: cur.execute(s)
            conn.commit()

run(DDL)
print("✅ schema ready")
