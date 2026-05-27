"""
Player ranking and filtering engine.
Scores all players and sorts them by various metrics.
"""

from typing import Optional
import pandas as pd

from src.api.models import Player
from src.scoring.calculator import score_player


def rank_players(players: list[Player]) -> pd.DataFrame:
    """Score all players and return a sorted DataFrame."""
    for p in players:
        score_player(p)

    rows = []
    for p in players:
        rows.append({
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "country": p.team_country,
            "club": p.club,
            "price": p.price,
            "ownership_%": round(p.ownership_pct, 1),
            "national_xPts": p.national_xpts_per_match,
            "club_xPts": p.club_xpts_per_match,
            "combined_xPts": p.combined_xpts_per_match,
            "value": p.value_score,
            "differential_score": p.differential_score,
            "is_differential": p.is_differential,
            # raw national stats
            "nat_goals": p.national_stats.goals,
            "nat_assists": p.national_stats.assists,
            "nat_matches": p.national_stats.matches,
            "nat_cs": p.national_stats.clean_sheets,
            "nat_sot": round(p.national_stats.shots_on_target, 1),
            "nat_chances": round(p.national_stats.chances_created, 1),
            "nat_tackles": round(p.national_stats.tackles, 1),
            "nat_saves": round(p.national_stats.saves, 1),
            "nat_yc": p.national_stats.yellow_cards,
            # raw club stats
            "club_goals": p.club_stats.goals,
            "club_assists": p.club_stats.assists,
            "club_matches": p.club_stats.matches,
            "club_cs": p.club_stats.clean_sheets,
            "club_sot": round(p.club_stats.shots_on_target, 1),
            "club_chances": round(p.club_stats.chances_created, 1),
            "club_tackles": round(p.club_stats.tackles, 1),
            "club_saves": round(p.club_stats.saves, 1),
            "club_yc": p.club_stats.yellow_cards,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("combined_xPts", ascending=False).reset_index(drop=True)
        df.index += 1  # 1-based rank
    return df


def filter_by_position(df: pd.DataFrame, position: str) -> pd.DataFrame:
    return df[df["position"] == position].copy()


def filter_by_country(df: pd.DataFrame, country: str) -> pd.DataFrame:
    return df[df["country"].str.lower() == country.lower()].copy()


def filter_by_club(df: pd.DataFrame, club: str) -> pd.DataFrame:
    return df[df["club"].str.lower() == club.lower()].copy()


def filter_by_budget(df: pd.DataFrame, max_price: float) -> pd.DataFrame:
    return df[df["price"] <= max_price].copy()


def top_differentials(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Players under 5% ownership with highest differential score."""
    return (
        df[df["is_differential"]]
        .sort_values("differential_score", ascending=False)
        .head(n)
    )


def best_value(df: pd.DataFrame, position: Optional[str] = None, n: int = 10) -> pd.DataFrame:
    """Best value-for-money players (xPts per $ spent)."""
    sub = filter_by_position(df, position) if position else df.copy()
    return sub.sort_values("value", ascending=False).head(n)


def get_country_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate stats per national team."""
    return (
        df.groupby("country")
        .agg(
            players=("name", "count"),
            avg_xPts=("combined_xPts", "mean"),
            total_xPts=("combined_xPts", "sum"),
            avg_price=("price", "mean"),
            avg_ownership=("ownership_%", "mean"),
        )
        .round(2)
        .sort_values("avg_xPts", ascending=False)
        .reset_index()
    )


def get_club_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate stats per club."""
    return (
        df[df["club"] != ""]
        .groupby("club")
        .agg(
            players=("name", "count"),
            avg_xPts=("combined_xPts", "mean"),
            total_xPts=("combined_xPts", "sum"),
            avg_price=("price", "mean"),
        )
        .round(2)
        .sort_values("avg_xPts", ascending=False)
        .reset_index()
    )
