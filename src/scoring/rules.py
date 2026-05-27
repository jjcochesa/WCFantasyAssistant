"""
FIFA World Cup Fantasy 2026 scoring rules.
Points are identical to UEFA Euro Fantasy.
"""

# Points by position code
POSITIONS = ["GK", "DEF", "MID", "FWD"]

# Minutes played thresholds
MINUTES_PLAYED_SHORT = 1   # +1 pt  (1-59 min)
MINUTES_PLAYED_FULL = 2    # +2 pts (60+ min)

SCORING = {
    # action: {position: points}
    "goal": {
        "GK": 6,
        "DEF": 6,
        "MID": 5,
        "FWD": 4,
    },
    "assist": {
        "GK": 3,
        "DEF": 3,
        "MID": 3,
        "FWD": 3,
    },
    "clean_sheet_60": {        # clean sheet if played 60+ min
        "GK": 5,
        "DEF": 5,
        "MID": 0,
        "FWD": 0,
    },
    "goal_outside_box_bonus": {  # extra point on top of goal
        "GK": 1,
        "DEF": 1,
        "MID": 1,
        "FWD": 1,
    },
    "goal_direct_fk_bonus": {
        "GK": 1,
        "DEF": 1,
        "MID": 1,
        "FWD": 1,
    },
    "penalty_save": {
        "GK": 5,
        "DEF": 0,
        "MID": 0,
        "FWD": 0,
    },
    "saves_per_3": {            # +1 per every 3 saves
        "GK": 1,
        "DEF": 0,
        "MID": 0,
        "FWD": 0,
    },
    "tackles_per_3": {          # +1 per every 3 tackles
        "GK": 0,
        "DEF": 0,
        "MID": 1,
        "FWD": 0,
    },
    "chances_created_per_2": {  # +1 per every 2 chances created
        "GK": 0,
        "DEF": 0,
        "MID": 1,
        "FWD": 0,
    },
    "shots_on_target_per_2": {  # +1 per every 2 shots on target
        "GK": 0,
        "DEF": 0,
        "MID": 0,
        "FWD": 1,
    },
    "yellow_card": {
        "GK": -1,
        "DEF": -1,
        "MID": -1,
        "FWD": -1,
    },
    "red_card": {
        "GK": -3,
        "DEF": -3,
        "MID": -3,
        "FWD": -3,
    },
    "own_goal": {
        "GK": -2,
        "DEF": -2,
        "MID": -2,
        "FWD": -2,
    },
    "penalty_missed": {
        "GK": -2,
        "DEF": -2,
        "MID": -2,
        "FWD": -2,
    },
    "goals_conceded_per_2_60min": {  # -1 per every 2 goals conceded (60+ min)
        "GK": -1,
        "DEF": -1,
        "MID": 0,
        "FWD": 0,
    },
    "potm": {                   # Player of the Match award
        "GK": 3,
        "DEF": 3,
        "MID": 3,
        "FWD": 3,
    },
    "low_ownership_bonus": {    # +2 if >4pts scored AND <5% ownership
        "GK": 2,
        "DEF": 2,
        "MID": 2,
        "FWD": 2,
    },
}
