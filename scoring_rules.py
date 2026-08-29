"""
Official UEFA Champions League Fantasy rules, 2026-27.

Transcribed from the in-game rules page — every value here is CONFIRMED, not
inferred. Earlier revisions of this file carried assumptions from the World Cup
game; the corrections are noted inline where they mattered.

Engine notes:
  - data_engine reads SCORING keys directly, so these values retune projections.
  - "Every 2 goals conceded: -1" is encoded as -0.5 per expected goal, because
    the engine works in expected goals rather than whole goals.
  - Goals from outside the box (+1), penalties won (+2), penalties conceded
    (-1) and Player of the Match (+3) are real scoring events we do NOT model:
    nothing in the data predicts them per player before a match. They are a
    reason a long-range shooter or a penalty-winning dribbler is worth slightly
    more than the projection shows.
"""

# ── Match scoring ─────────────────────────────────────────────────────────────
SCORING = {
    # All positions
    "minutes_1_to_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},
    "minutes_over_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},   # additional
    "assist":              {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},
    "tackles_per_3":       {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},   # balls recovered
    "yellow_card":         {"GK": -1, "DEF": -1, "MID": -1, "FWD": -1},
    "red_card":            {"GK": -3, "DEF": -3, "MID": -3, "FWD": -3},
    "own_goal":            {"GK": -2, "DEF": -2, "MID": -2, "FWD": -2},
    "penalty_miss":        {"GK": -2, "DEF": -2, "MID": -2, "FWD": -2},

    # Goals, by position
    "goal":                {"GK": 6, "DEF": 6, "MID": 5, "FWD": 4},

    # Clean sheets need 60+ minutes and survive a goal conceded after the player
    # is substituted off. Forwards get nothing.
    "clean_sheet_60":      {"GK": 4, "DEF": 4, "MID": 1, "FWD": 0},

    # -1 per EVERY 2 goals conceded, GK and DEF only -> -0.5 per expected goal
    "goals_conceded_1st":  {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "goals_conceded_add":  {"GK": -0.5, "DEF": -0.5, "MID": 0, "FWD": 0},

    # Goalkeeper only
    "saves_per_3":         {"GK": 1, "DEF": 0, "MID": 0, "FWD": 0},
    "penalty_save":        {"GK": 5, "DEF": 0, "MID": 0, "FWD": 0},

    # Real events, deliberately unmodelled (see module docstring)
    "goal_outside_box":    {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},   # on top of the goal
    "penalty_won":         {"GK": 2, "DEF": 2, "MID": 2, "FWD": 2},   # not for handball
    "penalty_conceded":    {"GK": -1, "DEF": -1, "MID": -1, "FWD": -1},
    "player_of_match":     {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},

    # Not part of UCL scoring — kept at zero so the engine's terms vanish.
    "chances_per_2":       {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "shots_on_target_per_2": {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
}

POSITIONS = ["GK", "DEF", "MID", "FWD"]

# ── Squad ─────────────────────────────────────────────────────────────────────
SQUAD_SLOTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}    # 15 players

BUDGET_GROUP = 100.0      # league phase
BUDGET_KNOCKOUT = 105.0   # rises to 105 after the league phase (was wrongly 100)

# A valid XI: exactly 1 GK, then at least this many of each outfield position.
XI_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}
XI_MAX = {"GK": 1, "DEF": 5, "MID": 5, "FWD": 3}
XI_SIZE = 11

# Max players from any one club, by stage. These were all too generous before —
# the knockout caps rise far more slowly than assumed.
MAX_PER_CLUB_BY_STAGE = {
    "league": 3,   # MD1-8
    "PO": 4,       # knockout phase play-offs (MD9-10)
    "R16": 4,      # was assumed 5
    "QF": 5,       # was assumed 6
    "SF": 6,       # was assumed 8
    "F": 8,        # was assumed 11
}
# App-facing aliases
MAX_PER_COUNTRY_GROUP = MAX_PER_CLUB_BY_STAGE["league"]
MAX_PER_COUNTRY_KNOCKOUT = MAX_PER_CLUB_BY_STAGE["R16"]

# ── Matchday map ──────────────────────────────────────────────────────────────
# 17 matchdays: 8 league, then two legs each of PO / R16 / QF / SF, then the final.
MATCHDAY_STAGE = {
    **{md: "league" for md in range(1, 9)},
    9: "PO", 10: "PO", 11: "R16", 12: "R16",
    13: "QF", 14: "QF", 15: "SF", 16: "SF", 17: "F",
}

# ── Transfers ─────────────────────────────────────────────────────────────────
# Free transfers available before each matchday. None means unlimited.
FREE_TRANSFERS = {
    1: None,                                   # before the league phase
    2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2,  # 2 per matchday in the league phase
    9: None,                                   # before the play-offs
    10: 2,                                     # play-offs second leg
    11: None,                                  # before the round of 16
    12: 3,                                     # round of 16 second leg
    13: 5, 14: 3,                              # quarter-finals
    15: 5, 16: 3,                              # semi-finals
    17: 5,                                     # final
}
TRANSFER_HIT = 4           # points deducted per transfer beyond the free quota
MAX_CARRIED_TRANSFERS = 1  # league phase only; nothing carries in the knockouts,
                           # and playing a chip forfeits any carry

# ── Chips ─────────────────────────────────────────────────────────────────────
# Two chips, one use each. Neither can be played on a matchday where everyone
# already gets unlimited transfers.
CHIPS = {
    "wildcard": {"unlimited_transfers": True, "unlimited_budget": False,
                 "squad_persists": True},
    "limitless": {"unlimited_transfers": True, "unlimited_budget": True,
                  "squad_persists": False},   # squad reverts after the matchday
}
CHIP_BLOCKED_MATCHDAYS = {1, 9, 11}

# ── Substitutions ─────────────────────────────────────────────────────────────
# Correcting an earlier note in this file: subs WITHIN a matchday are capped,
# not unlimited. Between matchdays you can reshuffle the XI freely; but after a
# day's matches finish, you may sub out at most SUBS_PER_DAY players, and only
# for players whose clubs have not yet played that matchday. A player subbed out
# scores 0 for the matchday.
SUBS_PER_DAY = 4
# MD8 and MD17 kick off simultaneously, so no in-matchday subs are possible.
NO_SUB_MATCHDAYS = {8, 17}

# Captaincy doubles that player's matchday score, and can be moved to a player
# whose club has not yet played — the original captain's double is then lost.
CAPTAIN_MULTIPLIER = 2

# Prices are fixed until the MD2 deadline, then move with performance from MD3.
PRICE_CHANGES_FROM_MATCHDAY = 3


def free_transfers(matchday: int):
    """Free transfers before this matchday; None means unlimited."""
    return FREE_TRANSFERS.get(matchday, 0)


def max_per_club(matchday: int) -> int:
    return MAX_PER_CLUB_BY_STAGE[MATCHDAY_STAGE.get(matchday, "league")]


def budget(matchday: int) -> float:
    return BUDGET_GROUP if MATCHDAY_STAGE.get(matchday, "league") == "league" \
        else BUDGET_KNOCKOUT


# Retained so older imports don't break; UCL Fantasy has no scout bonus.
SCOUT_OWNERSHIP_THRESHOLD = 0.0
SCOUT_POINTS_THRESHOLD = float("inf")
