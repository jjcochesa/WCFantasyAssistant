"""
Official FIFA World Cup Fantasy 2026 scoring rules.
Source: Official game instructions.
"""

# Points by position — exact from official rules
SCORING = {
    "minutes_1_to_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},
    "minutes_over_60":     {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},  # additional
    "goal":                {"GK": 9, "DEF": 7, "MID": 6, "FWD": 5},
    "assist":              {"GK": 3, "DEF": 3, "MID": 3, "FWD": 3},
    "clean_sheet_60":      {"GK": 5, "DEF": 5, "MID": 1, "FWD": 0},
    "goals_conceded_1st":  {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0},   # first goal: no deduction
    "goals_conceded_add":  {"GK":-1, "DEF":-1, "MID": 0, "FWD": 0},   # each additional goal
    "saves_per_3":         {"GK": 1, "DEF": 0, "MID": 0, "FWD": 0},
    "penalty_save":        {"GK": 3, "DEF": 0, "MID": 0, "FWD": 0},
    "tackles_per_3":       {"GK": 0, "DEF": 0, "MID": 1, "FWD": 0},
    "chances_per_2":       {"GK": 0, "DEF": 0, "MID": 1, "FWD": 0},
    "shots_on_target_per_2": {"GK": 0, "DEF": 0, "MID": 0, "FWD": 1},
    "yellow_card":         {"GK":-1, "DEF":-1, "MID":-1, "FWD":-1},
    "red_card":            {"GK":-2, "DEF":-2, "MID":-2, "FWD":-2},
    "own_goal":            {"GK":-2, "DEF":-2, "MID":-2, "FWD":-2},
    "draw_penalty":        {"GK": 2, "DEF": 2, "MID": 2, "FWD": 2},  # winning a penalty
    "concede_penalty":     {"GK":-1, "DEF":-1, "MID":-1, "FWD":-1},  # fouling for penalty
    "direct_fk_goal":      {"GK": 1, "DEF": 1, "MID": 1, "FWD": 1},  # bonus on top of goal
    "scout_bonus":         {"GK": 2, "DEF": 2, "MID": 2, "FWD": 2},  # >4pts AND <5% ownership
}

POSITIONS = ["GK", "DEF", "MID", "FWD"]

SQUAD_SLOTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
BUDGET_GROUP = 100.0
BUDGET_KNOCKOUT = 105.0
MAX_PER_COUNTRY_GROUP = 3
SCOUT_OWNERSHIP_THRESHOLD = 4.5
SCOUT_POINTS_THRESHOLD = 4.0
