<p align="center">
  <img src="assets/clash-royale.png" alt="Clash Royale Analytics" width="820">
</p>

# Clash Royale Analytics

**What this is:** A hands-on data pipeline + analysis that pulls live Clash Royale data from the official Clash Royale API, builds tidy CSV datasets, and generates clear visuals of **card usage rates** and **win rates** overall and **by trophy tier**. Designed to be easy to run locally and straightforward to evaluate.

---

## Highlights

- **End-to-end pipeline:** From API ingestion → data normalization → analysis → charts.
- **Clean modeling:** Ensures each battle is counted once (deduped), derives a single winner per match, and computes usage/win metrics correctly (denominator fixes to avoid filter traps).
- **Actionable metrics:**
  - **Card Usage Rate:** % of battles where a card appears (overall and per trophy bin).
  - **Card Win %:** Share of battles where the **winning deck** contained the card.
  - **Per-Trophy Bins:** Defaults to 5,000-point bins up to 15,000 trophies for meta trends by skill tier.
- **Results as files:** CSVs + Matplotlib PNGs (easy to inspect, email, or drop into slides).
- **BI-ready:** The same CSVs power a Power BI model with measures for usage/win-rate and slicers (arena, mode, date).

---

## Tech & Skills Demonstrated

- **Python** (requests, pandas, numpy, matplotlib), **dotenv**
- Robust HTTP calls with pagination, backoff, and IPv4 handling where needed
- Data shaping in pandas (groupby, joins, binning, deduplication)
- Metric design (correct denominators, winner attribution)
- Visualization for insights (ranked bar charts, per-bin trend lines)
- **Power BI** star-schema modeling and DAX measures

---

## Data Flow (At a Glance)

1. **Fetch reference data:** `cards.csv`
2. **Discover entities:** `clans.txt` → `players.csv`
3. **Collect facts:** `battles_raw.csv` + `battle_cards_raw.csv`
4. **Analyze:** compute usage rate & win % overall and per-trophy-bin
5. **Output:** `analysis_out/*.csv` and `analysis_out/*.png` (top cards and per-bin charts)

---

## Example Outputs

- **cards_summary_overall.csv** — appearances, usage_rate, wins_with_card, win_rate
- **cards_summary_per_trophy_bin.csv** — same metrics per bin (e.g., `10000–14999`)
- **most_used_cards.png** — overall usage rate (Top-N)
- **best_winrate_cards.png** — overall win % (Top-N, with sample threshold)
- **avg_usage_rate_by_bin.png** — meta overview across trophy tiers
- **bin_<range>_most_used.png / bin_<range>_best_winrate.png** — per-bin charts

(Charts are Matplotlib; easy to embed in reports.)

---

## Quick Run (minimal)

```bash
# Create venv & install
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install requests python-dotenv pandas numpy matplotlib
echo "CR_TOKEN=YOUR_API_TOKEN" > .env

# Pipeline (files only; no DB)
python 01_load_cards_csv.py
python 02_random_clans.py
python 03_random_players_from_clans.py
python 04_pull_battles_for_players.py

# Analysis (defaults: 5k trophy bins up to 15k)
python 05_analyze_data.py