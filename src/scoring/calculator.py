"""
Expected points per match calculator.
Uses per-90 stat rates × scoring rules to estimate xPts for a future match.
"""

from src.api.models import Player, PlayerStats
from src.scoring.rules import SCORING, MINUTES_PLAYED_FULL, MINUTES_PLAYED_SHORT
from config import LOW_OWNERSHIP_THRESHOLD, LOW_OWNERSHIP_BONUS


def _get(action: str, position: str) -> float:
    return SCORING.get(action, {}).get(position, 0)


def calculate_xpts(stats: PlayerStats, position: str, ownership_pct: float = 100.0) -> float:
    """
    Estimate expected points for one match given historical per-match rates.
    All stat arguments are per-match averages (not per-90).
    """
    if stats.matches == 0:
        return 0.0

    xpts = 0.0
    pos = position

    # Appearance bonus — assume full game played (60+ min)
    xpts += MINUTES_PLAYED_FULL

    # Goals — use per-match rate
    goals_pm = stats.goals / stats.matches
    xpts += goals_pm * _get("goal", pos)

    # Assists
    assists_pm = stats.assists / stats.matches
    xpts += assists_pm * _get("assist", pos)

    # Clean sheets (fraction of matches with clean sheet)
    cs_rate = stats.clean_sheets / stats.matches
    xpts += cs_rate * _get("clean_sheet_60", pos)

    # Goals conceded (GK/DEF penalty)
    if pos in ("GK", "DEF"):
        gc_pm = stats.goals_conceded / stats.matches
        # -1 per every 2 conceded (when playing 60+ min)
        xpts += (gc_pm / 2) * _get("goals_conceded_per_2_60min", pos)

    # Saves (GK) — +1 per every 3
    if pos == "GK":
        saves_pm = stats.saves / stats.matches
        xpts += (saves_pm / 3) * _get("saves_per_3", pos)
        pen_saves_pm = stats.penalties_saved / stats.matches
        xpts += pen_saves_pm * _get("penalty_save", pos)

    # Tackles (MID) — +1 per every 3
    if pos == "MID":
        tackles_pm = stats.tackles / stats.matches
        xpts += (tackles_pm / 3) * _get("tackles_per_3", pos)
        cc_pm = stats.chances_created / stats.matches
        xpts += (cc_pm / 2) * _get("chances_created_per_2", pos)

    # Shots on target (FWD) — +1 per every 2
    if pos == "FWD":
        sot_pm = stats.shots_on_target / stats.matches
        xpts += (sot_pm / 2) * _get("shots_on_target_per_2", pos)

    # Disciplinary deductions
    yc_pm = stats.yellow_cards / stats.matches
    xpts += yc_pm * _get("yellow_card", pos)

    rc_pm = stats.red_cards / stats.matches
    xpts += rc_pm * _get("red_card", pos)

    og_pm = stats.own_goals / stats.matches
    xpts += og_pm * _get("own_goal", pos)

    pm_pm = stats.penalties_missed / stats.matches
    xpts += pm_pm * _get("penalty_missed", pos)

    # Low-ownership bonus expectation
    # If player scores >4 pts AND is owned by <5%, they earn +2
    # We model this as: probability(>4pts) × bonus × (1 if differential)
    if ownership_pct < LOW_OWNERSHIP_THRESHOLD and xpts > 4:
        xpts += LOW_OWNERSHIP_BONUS

    return round(xpts, 2)


def score_player(player: Player) -> Player:
    """Fill all computed score fields on a Player object in-place."""
    player.national_xpts_per_match = calculate_xpts(
        player.national_stats, player.position, player.ownership_pct
    )
    player.club_xpts_per_match = calculate_xpts(
        player.club_stats, player.position, player.ownership_pct
    )

    from config import NATIONAL_TEAM_WEIGHT, CLUB_FORM_WEIGHT
    has_national = player.national_stats.matches > 0
    has_club = player.club_stats.matches > 0

    if has_national and has_club:
        player.combined_xpts_per_match = (
            player.national_xpts_per_match * NATIONAL_TEAM_WEIGHT
            + player.club_xpts_per_match * CLUB_FORM_WEIGHT
        )
    elif has_national:
        player.combined_xpts_per_match = player.national_xpts_per_match
    else:
        player.combined_xpts_per_match = player.club_xpts_per_match

    if player.price > 0:
        player.value_score = round(player.combined_xpts_per_match / player.price, 3)

    # Differential score: multiply by 1.2x if low ownership
    diff_mult = 1.2 if player.is_differential else 1.0
    player.differential_score = round(player.combined_xpts_per_match * diff_mult, 2)

    return player
