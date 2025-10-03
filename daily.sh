#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

# Load .env (simple; avoid spaces in values)
export $(grep -v '^#' .env | xargs)

python3 01_init_schema.py
python3 02_load_cards.py
python3 03_random_clans.py
python3 04_random_players_from_clans.py
python3 05_pull_battles_for_players.py
python3 06_load_csv_to_db.py
python3 07_retention_90d.py

echo "Done: $(date)"
