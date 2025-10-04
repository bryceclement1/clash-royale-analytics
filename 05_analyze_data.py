#!/usr/bin/env python3
# analyze_data.py — battle-level stats w/ trophy bins (Python 3.9+)
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def parse_args():
    p = argparse.ArgumentParser("Analyze Clash Royale CSVs: usage rate, win %, and per-trophy-bin.")
    p.add_argument("--battles", default="battles_raw.csv")
    p.add_argument("--battle-cards", default="battle_cards_raw.csv")
    p.add_argument("--cards", default="cards.csv")
    p.add_argument("--outdir", default="analysis_out")
    p.add_argument("--topn", type=int, default=30)
    p.add_argument("--min-sample", type=int, default=50)
    p.add_argument("--bin-size", type=int, default=5000)
    p.add_argument("--min-trophy", type=int, default=0)
    p.add_argument("--max-trophy", type=int, default=15000)
    return p.parse_args()

def ensure_outdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def barh(df, x_col, y_col, title, outpng):
    plt.figure()
    ax = df.plot(kind="barh", x=y_col, y=x_col, legend=False)
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(outpng, dpi=140)
    plt.close()

def sanitize_bin_label(lbl: str) -> str:
    # e.g., "5000-9999" -> "5000_9999"
    return str(lbl).replace(" ", "").replace("-", "_").replace("[", "").replace(")", "").replace("(", "").replace(",", "_")

def barh_simple(df, value_col, label_col, title, outpng):
    plt.figure()
    ax = df.plot(kind="barh", x=label_col, y=value_col, legend=False)
    ax.set_title(title)
    ax.set_xlabel(value_col)
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(outpng, dpi=140)
    plt.close()

def line(df, x_col, y_col, title, outpng):
    plt.figure()
    ax = df.plot(x=x_col, y=y_col, legend=False)
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.tight_layout()
    plt.savefig(outpng, dpi=140)
    plt.close()

def build_battle_level(battles: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one row per battle_id and decide winner_side."""
    # Defensive: normalize names
    battles = battles.copy()
    battles.columns = [c.strip() for c in battles.columns]

    # We’ll use crowns to infer the winner per row
    if not {"player_crowns", "opponent_crowns"}.issubset(battles.columns):
        raise SystemExit("battles_raw.csv needs player_crowns and opponent_crowns.")

    # Mean trophies per ROW -> then average within battle_id
    if {"player_trophies", "opponent_trophies"}.issubset(battles.columns):
        battles["mean_trophies_row"] = battles[["player_trophies", "opponent_trophies"]].mean(axis=1)
    elif "player_trophies" in battles.columns:
        battles["mean_trophies_row"] = battles["player_trophies"].astype(float)
    else:
        battles["mean_trophies_row"] = np.nan

    # Crown diff per row (player perspective for that row)
    battles["crown_diff_row"] = battles["player_crowns"].astype(int) - battles["opponent_crowns"].astype(int)

    # Winner per battle_id: if ANY row has diff>0 -> winner_side='player', elif ANY diff<0 -> 'opponent'
    def decide_winner(s):
        if (s > 0).any():
            return "player"
        if (s < 0).any():
            return "opponent"
        return np.nan  # tie / undefined

    winner = battles.groupby("battle_id")["crown_diff_row"].apply(decide_winner).rename("winner_side")
    mean_trophies = battles.groupby("battle_id")["mean_trophies_row"].mean().rename("mean_trophies")

    out = pd.concat([winner, mean_trophies], axis=1).reset_index()
    return out  # columns: battle_id, winner_side, mean_trophies

def main():
    args = parse_args()
    outdir = Path(args.outdir)
    ensure_outdir(outdir)

    # Load
    battles = pd.read_csv(args.battles)
    bcards = pd.read_csv(args.battle_cards)
    cards  = pd.read_csv(args.cards)

    for need_col in ["battle_id", "card_id"]:
        if need_col not in bcards.columns:
            raise SystemExit(f"battle_cards_raw.csv must contain '{need_col}'.")
    if "side" not in bcards.columns:
        raise SystemExit("battle_cards_raw.csv must contain 'side' (player/opponent) to compute win%.")

    if "battle_id" not in battles.columns:
        raise SystemExit("battles_raw.csv must contain 'battle_id'.")

    # Card id -> name
    card_name = {}
    if {"id", "name"}.issubset(cards.columns):
        card_name = dict(zip(cards["id"], cards["name"]))

    # Build one-row-per-battle table
    b_lvl = build_battle_level(battles)
    total_battles = b_lvl["battle_id"].nunique()

    # ---------------- Overall usage & win% ----------------
    # Usage: in how many unique battles does card appear (either side)?
    app = (
        bcards.groupby(["card_id"])["battle_id"]
        .nunique()
        .rename("appearances")
        .reset_index()
    )

    # Wins with card: join winner_side and keep rows where the card is on the winner's side
    bc_winner = bcards.merge(b_lvl[["battle_id", "winner_side"]], on="battle_id", how="inner")
    wins = (
        bc_winner[bc_winner["side"] == bc_winner["winner_side"]]
        .groupby("card_id")["battle_id"]
        .nunique()
        .rename("wins_with_card")
        .reset_index()
    )

    summary = app.merge(wins, on="card_id", how="left").fillna({"wins_with_card": 0})
    summary["usage_rate"] = summary["appearances"] / float(total_battles)
    summary["win_rate"]   = np.where(summary["appearances"] > 0,
                                     summary["wins_with_card"] / summary["appearances"],
                                     np.nan)
    summary["card_name"]  = summary["card_id"].map(card_name).fillna(summary["card_id"].astype(str))

    summary_out = summary.sort_values("appearances", ascending=False)
    summary_out.to_csv(outdir / "cards_summary_overall.csv", index=False)

    # Plots: overall
    topN = args.topn
    min_sample = args.min_sample

    most_used = summary_out.head(topN)[["usage_rate", "card_name"]]
    barh(most_used.iloc[::-1], "usage_rate", "card_name",
         f"Top {topN} Most Used Cards (Usage Rate = appearances / total battles)",
         outdir / "most_used_cards.png")

    best_wr = (
        summary_out[summary_out["appearances"] >= min_sample]
        .sort_values("win_rate", ascending=False)
        .head(topN)[["win_rate", "card_name"]]
    )
    barh(best_wr.iloc[::-1], "win_rate", "card_name",
         f"Top {topN} Card Win % (min {min_sample} battles where card present)",
         outdir / "best_winrate_cards.png")

    # ---------------- Per-trophy-bin usage & win% ----------------
    # Create bins from battle-level mean_trophies
    bins = np.arange(args.min_trophy, args.max_trophy + args.bin_size, args.bin_size)
    labels = [f"{b}-{b+args.bin_size-1}" for b in bins[:-1]]
    b_lvl["trophy_bin"] = pd.cut(b_lvl["mean_trophies"], bins=bins, labels=labels, right=False)

    # Denominator per bin = # of unique battles in that bin
    denom = (
        b_lvl.dropna(subset=["trophy_bin"])
        .groupby("trophy_bin")["battle_id"]
        .nunique()
        .rename("total_battles_bin")
        .reset_index()
    )

    # Appearances per (card, bin) = distinct battles in that bin where the card appeared (either side)
    bc_bin = bcards.merge(b_lvl[["battle_id", "trophy_bin", "winner_side"]], on="battle_id", how="inner")
    app_bin = (
        bc_bin.dropna(subset=["trophy_bin"])
        .groupby(["card_id", "trophy_bin"])["battle_id"]
        .nunique()
        .rename("appearances")
        .reset_index()
    )

    # Wins per (card, bin) = distinct battles in that bin where winner's deck contained the card
    wins_bin = (
        bc_bin[(bc_bin["side"] == bc_bin["winner_side"]) & (~bc_bin["trophy_bin"].isna())]
        .groupby(["card_id", "trophy_bin"])["battle_id"]
        .nunique()
        .rename("wins_with_card")
        .reset_index()
    )

    per_bin = app_bin.merge(wins_bin, on=["card_id","trophy_bin"], how="left").fillna({"wins_with_card":0})
    per_bin = per_bin.merge(denom, on="trophy_bin", how="left")
    per_bin["usage_rate"] = per_bin["appearances"] / per_bin["total_battles_bin"]
    per_bin["win_rate"]   = np.where(per_bin["appearances"] > 0,
                                     per_bin["wins_with_card"] / per_bin["appearances"],
                                     np.nan)
    per_bin["card_name"]  = per_bin["card_id"].map(card_name).fillna(per_bin["card_id"].astype(str))

    per_bin_out = per_bin.sort_values(["trophy_bin","appearances"], ascending=[True, False])
    per_bin_out.to_csv(outdir / "cards_summary_per_trophy_bin.csv", index=False)
    
    # ---------- NEW: per-bin charts ----------
    # We'll create two charts per trophy bin: Most Used, and Highest Win %
    per_bin_min_sample = max(10, args.min_sample // 2)  # a bit looser than overall
    bins_present = (
        per_bin.dropna(subset=["trophy_bin"])["trophy_bin"]
        .astype(str)
        .unique()
    )

    for bin_lbl in bins_present:
        sub = per_bin[per_bin["trophy_bin"].astype(str) == bin_lbl].copy()
        if sub.empty:
            continue

        # MOST USED in this bin (by usage_rate)
        top_used_bin = (
            sub.sort_values("usage_rate", ascending=False)
            .head(args.topn)[["card_name", "usage_rate"]]
        )
        if not top_used_bin.empty:
            out_png = outdir / f"bin_{sanitize_bin_label(bin_lbl)}_most_used.png"
            barh_simple(
                top_used_bin.iloc[::-1],
                "usage_rate",
                "card_name",
                f"Most Used Cards — Usage Rate — Trophy Bin {bin_lbl}",
                out_png
            )

        # BEST WIN RATE in this bin (apply per-bin sample threshold)
        top_wr_bin = (
            sub[sub["appearances"] >= per_bin_min_sample]
            .sort_values("win_rate", ascending=False)
            .head(args.topn)[["card_name", "win_rate"]]
        )
        if not top_wr_bin.empty:
            out_png = outdir / f"bin_{sanitize_bin_label(bin_lbl)}_best_winrate.png"
            barh_simple(top_wr_bin.iloc[::-1], "win_rate", "card_name",
                        f"Highest Win % (min {per_bin_min_sample} battles) — Trophy Bin {bin_lbl}",
                        out_png)


        # Win% by bin for top 10 most-used cards overall
        top10 = summary_out.head(10)["card_id"].tolist()
        for cid in top10:
            sub = (
                per_bin[per_bin["card_id"] == cid]
                .sort_values("trophy_bin")[["trophy_bin","win_rate"]]
                .dropna()
            )
            if sub.empty:
                continue
            cname = card_name.get(cid, str(cid))
            line(sub, "trophy_bin", "win_rate",
                f"Win % by Trophy Bin — {cname}",
                outdir / f"winrate_by_bin_{cname}.png")

    print(f"✅ Done. Outputs in {outdir.resolve()}")
    print(" - cards_summary_overall.csv")
    print(" - cards_summary_per_trophy_bin.csv")
    print(" - most_used_cards.png")
    print(" - best_winrate_cards.png")
    print(" - avg_usage_rate_by_bin.png")
    print(" - winrate_by_bin_<cardid>.png (top 10)")

if __name__ == "__main__":
    main()
