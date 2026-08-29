"""
Official UEFA Champions League Fantasy scoring rules (gaming.uefa.com).

VERIFICATION STATUS — read before trusting a number.

  CONFIRMED for 2026-27 (UEFA rules article + press coverage, Aug 2026):
    appearance 1, +1 more at 60 minutes
    goal: FWD 4, MID 5, DEF 6, GK 6
    goal from OUTSIDE THE BOX: +1 on top
    penalty WON: +2 (not when the penalty is for handball)
    ball recoveries: +1 per 3, all positions
    Player of the Match: +3
    clean sheet needs 60+ minutes, and is unaffected if the player is already
      off when the goal goes in

  NOT YET CONFIRMED — carried over from 24-25/25-26 and still to be checked
  against the in-game Rules page:
    assist value, clean-sheet value by position, goals-conceded penalty,
    saves, penalty save, penalty miss, yellow/red card, own goal

The unconfirmed ones are the defensive side, which is exactly where the cheap
picks live, so they are worth checking before locking a squad.

Engine notes:
  - data_engine reads SCORING keys directly (goal / assist / clean_sheet_60 /
    goals_conceded_add), so these values retune all projections.
  - UCL deducts -1 per EVERY 2 goals conceded (GK/DEF). The engine applies its
    value per expected goal beyond the first, so we encode -0.5 per goal.
  - UCL awards 1pt per 3 BALL RECOVERIES (all positions), now fed by real
    recovery data (tackles + interceptions) rather than a tackles-only proxy.
  - Player of the Match (+3), goals from outside the box (+1) and penalties won
    (+2) are real scoring events we do NOT model: nothing in the data predicts
    them per player before a match, so including them would add noise rather
    than signal. They are listed below for completeness and are a reason a
    long-range shooter or a penalty-winning dribbler is worth slightly more
    than the projection shows.
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
    # Ball recoveries: 1pt per 3, ALL positions in UCL. CONFIRMED.
    "tackles_per_3":       {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},
    # Not part of UCL scoring (were WC-specific) — zeroed so the engine's terms vanish.
    "chances_per_2":       {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "shots_on_target_per_2": {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},
    "yellow_card":         {"GK": -1, "DEF": -1, "MID": -1, "FWD": -1},
    "red_card":            {"GK": -3, "DEF": -3, "MID": -3, "FWD": -3},
    "own_goal":            {"GK": -2, "DEF": -2, "MID": -2, "FWD": -2},
    # Real scoring events, listed for completeness but deliberately unmodelled —
    # nothing in the data predicts them per player before a match.
    "player_of_match":     {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},
    "goal_outside_box":    {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},   # on top of the goal
    "penalty_won":         {"GK": 2, "DEF": 2, "MID": 2, "FWD": 2},   # not for handball
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

# There is no scout bonus in UCL Fantasy — it was a World Cup game feature.
# These thresholds remain only so older imports don't break; nothing scores off
# them any more.
SCOUT_OWNERSHIP_THRESHOLD = 0.0
SCOUT_POINTS_THRESHOLD = float("inf")
