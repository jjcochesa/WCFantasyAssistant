"""
Official UEFA Champions League Fantasy scoring rules (gaming.uefa.com).

Values from the 24-25/25-26 editions of the game — UEFA keeps scoring stable
year to year, but re-verify against the in-game rules page when the 2026-27
game opens in August (especially the per-club caps and transfer allowances).

Engine notes:
  - data_engine reads SCORING keys directly (goal / assist / clean_sheet_60 /
    goals_conceded_add), so these values retune all projections.
  - UCL deducts -1 per EVERY 2 goals conceded (GK/DEF). The engine applies its
    value per expected goal beyond the first, so we encode -0.5 per goal.
  - UCL awards 1pt per 3 BALL RECOVERIES (all positions). Our stats pipeline
    tracks tackles, a conservative proxy — encoded under tackles_per_3.
  - Player of the Match (+3) is not predictable per-player pre-match; it is
    intentionally NOT modelled (would just add noise).
"""

# Points by position — official UCL Fantasy match scoring
SCORING = {
    "minutes_1_to_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},
    "minutes_over_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},  # additional (2 total)
    "goal":                {"GK": 6, "DEF": 6, "MID": 5, "FWD": 4},
    "assist":              {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},
    "clean_sheet_60":      {"GK": 4, "DEF": 4, "MID": 1, "FWD": 0},
    "goals_conceded_1st":  {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    # -1 per 2 conceded (GK/DEF) -> -0.5 per expected goal beyond the first
    "goals_conceded_add":  {"GK": -0.5, "DEF": -0.5, "MID": 0, "FWD": 0},
    "saves_per_3":         {"GK": 1, "DEF": 0, "MID": 0, "FWD": 0},
    "penalty_save":        {"GK": 5, "DEF": 0, "MID": 0, "FWD": 0},
    "penalty_miss":        {"GK": -2, "DEF": -2, "MID": -2, "FWD": -2},
    # Ball recoveries: 1pt per 3, ALL positions in UCL. Tackles are our proxy
    # (undercounts for GKs/forwards; closest signal we track per-90).
    "tackles_per_3":       {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},
    # Not part of UCL scoring (were WC-specific) — zeroed so the engine's terms vanish.
    "chances_per_2":       {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "shots_on_target_per_2": {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "yellow_card":         {"GK": -1, "DEF": -1, "MID": -1, "FWD": -1},
    "red_card":            {"GK": -3, "DEF": -3, "MID": -3, "FWD": -3},
    "own_goal":            {"GK": -2, "DEF": -2, "MID": -2, "FWD": -2},
    # Player of the Match: +3 in the real game — deliberately unmodelled (see above).
    "player_of_match":     {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},
    # App-level scout bonus (our feature, not UEFA's): low-owned high-scorers.
    "scout_bonus":         {"GK": 2, "DEF": 2, "MID": 2, "FWD": 2},
}

POSITIONS = ["GK", "DEF", "MID", "FWD"]

# ── Squad rules ────────────────────────────────────────────────────────────────
SQUAD_SLOTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}   # 15-man squad
BUDGET_GROUP = 100.0      # league phase budget (€m) — confirmed from the
                          # game feed: constraints_90.json maxTeamValue = "100"
BUDGET_KNOCKOUT = 100.0   # assume unchanged; re-check the feed at the playoff round

# Per-CLUB cap by stage. League phase: 3 per club; the cap relaxes each knockout
# round as clubs drop out. VERIFY against the in-game rules when 26-27 opens.
MAX_PER_CLUB_BY_STAGE = {
    "league": 3,   # MD1–MD8 — confirmed: constraints_90.json maxTeamPlayers = 3
    "PO": 4,       # knockout playoff (16 clubs)
    "R16": 5,
    "QF": 6,
    "SF": 8,
    "F": 11,       # two clubs left — cap effectively off
}
# App-facing aliases (imported by app.py sliders)
MAX_PER_COUNTRY_GROUP = MAX_PER_CLUB_BY_STAGE["league"]
MAX_PER_COUNTRY_KNOCKOUT = MAX_PER_CLUB_BY_STAGE["R16"]

# ── Matchday mechanics (documented for the assistant's advice; not engine inputs) ──
# - Captain: 2x points, changeable each matchday.
# - UNLIMITED substitutions from your 15 BETWEEN days within a matchday — bench
#   players who already played can be swapped for ones playing tomorrow. This is
#   the single biggest UCL-vs-WC strategic difference: bench depth scores.
# - Transfers between MDs + Wildcard/boosters: allowances vary by stage and
#   edition — pull exact numbers from the in-game rules page when 26-27 opens.

SCOUT_OWNERSHIP_THRESHOLD = 4.5
SCOUT_POINTS_THRESHOLD = 4.0
