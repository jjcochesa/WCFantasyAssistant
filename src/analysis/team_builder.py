"""
Optimal team builder — picks the best 15-player squad within budget constraints.
Uses a greedy approach: fill each slot with the highest combined_xPts player
that fits the remaining budget and squad rules.
"""

import pandas as pd
from typing import Optional

SQUAD_RULES = {
    "GK":  {"min": 2, "max": 2},
    "DEF": {"min": 5, "max": 5},
    "MID": {"min": 5, "max": 5},
    "FWD": {"min": 3, "max": 3},
}
TOTAL_SQUAD = 15
MAX_PLAYERS_PER_COUNTRY = 3  # nationality cap


def build_best_squad(
    df: pd.DataFrame,
    budget: float = 100.0,
    sort_by: str = "combined_xPts",
    country_cap: int = MAX_PLAYERS_PER_COUNTRY,
) -> pd.DataFrame:
    """
    Greedy squad builder.
    Returns a DataFrame of 15 selected players sorted by position + xPts.
    """
    selected = []
    country_counts: dict[str, int] = {}
    remaining_budget = budget

    for pos, rules in SQUAD_RULES.items():
        target = rules["max"]
        candidates = (
            df[df["position"] == pos]
            .sort_values(sort_by, ascending=False)
            .copy()
        )
        added = 0
        for _, row in candidates.iterrows():
            if added >= target:
                break
            country = row["country"]
            price = row["price"]
            if price > remaining_budget:
                continue
            if country_counts.get(country, 0) >= country_cap:
                continue
            selected.append(row)
            remaining_budget -= price
            country_counts[country] = country_counts.get(country, 0) + 1
            added += 1

    if not selected:
        return pd.DataFrame()

    result = pd.DataFrame(selected)
    pos_order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
    result["_pos_order"] = result["position"].map(pos_order)
    result = result.sort_values(["_pos_order", sort_by], ascending=[True, False])
    result = result.drop(columns=["_pos_order"]).reset_index(drop=True)
    result.index += 1

    total_cost = result["price"].sum()
    total_xpts = result["combined_xPts"].sum()

    print(f"Squad cost: ${total_cost:.1f}m | Budget remaining: ${budget - total_cost:.1f}m")
    print(f"Total combined xPts: {total_xpts:.1f}")

    return result


def suggest_captain(squad_df: pd.DataFrame) -> pd.Series:
    """Return the player with highest combined_xPts as captain pick."""
    return squad_df.sort_values("combined_xPts", ascending=False).iloc[0]
