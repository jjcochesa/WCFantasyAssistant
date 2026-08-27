"""
UEFA Champions League 2026-27 league-phase draw (27 August 2026).

Transcribed from the official pot-by-pot draw grids. Each club plays 8 different
opponents — two from every pot, one home and one away — so the entry below
mirrors the published table exactly and is easy to re-check against the source
images.

    DRAW[club] = {"pot": n, "h": [pot1_home, pot2_home, pot3_home, pot4_home],
                             "a": [pot1_away, pot2_away, pot3_away, pot4_away]}

scripts/build_draw.py expands this into the 144 fixtures and validates that
every tie is listed by both clubs, that each club has 4 home and 4 away games,
and that the pot structure holds.
"""

# 3-letter codes -> display names (the 36 participants)
CLUBS = {
    # Pot 1
    "PSG": "Paris Saint-Germain", "BAY": "Bayern München", "RMA": "Real Madrid",
    "LIV": "Liverpool", "INT": "Inter", "MCI": "Manchester City",
    "ARS": "Arsenal", "BAR": "Barcelona", "ATM": "Atlético Madrid",
    # Pot 2
    "DOR": "Borussia Dortmund", "ROM": "Roma", "SPO": "Sporting CP",
    "AVL": "Aston Villa", "POR": "Porto", "MUN": "Manchester United",
    "CLB": "Club Brugge", "BET": "Real Betis", "PSV": "PSV",
    # Pot 3
    "FEY": "Feyenoord", "LIL": "Lille", "BOD": "Bodø/Glimt", "NAP": "Napoli",
    "RBL": "RB Leipzig", "VIL": "Villarreal", "FEN": "Fenerbahçe",
    "SHK": "Shakhtar Donetsk", "GAL": "Galatasaray",
    # Pot 4
    "SLA": "Slavia Praha", "SLB": "Slovan Bratislava", "STU": "VfB Stuttgart",
    "AEK": "AEK Athens", "LSK": "LASK", "COM": "Como", "LEN": "Lens",
    "VIK": "Viking", "SAB": "Sabah",
}

POTS = {
    1: ["PSG", "BAY", "RMA", "LIV", "INT", "MCI", "ARS", "BAR", "ATM"],
    2: ["DOR", "ROM", "SPO", "AVL", "POR", "MUN", "CLB", "BET", "PSV"],
    3: ["FEY", "LIL", "BOD", "NAP", "RBL", "VIL", "FEN", "SHK", "GAL"],
    4: ["SLA", "SLB", "STU", "AEK", "LSK", "COM", "LEN", "VIK", "SAB"],
}

# h / a are ordered by opponent pot: [vs Pot1, vs Pot2, vs Pot3, vs Pot4]
DRAW = {
    # ── Pot 1 ────────────────────────────────────────────────────────────────
    "PSG": {"pot": 1, "h": ["BAR", "ROM", "GAL", "SLB"], "a": ["MCI", "AVL", "VIL", "COM"]},
    "BAY": {"pot": 1, "h": ["ARS", "BET", "BOD", "SLA"], "a": ["ATM", "MUN", "LIL", "VIK"]},
    "RMA": {"pot": 1, "h": ["INT", "PSV", "RBL", "LSK"], "a": ["ARS", "ROM", "SHK", "AEK"]},
    "LIV": {"pot": 1, "h": ["ATM", "POR", "VIL", "LEN"], "a": ["INT", "CLB", "FEN", "LSK"]},
    "INT": {"pot": 1, "h": ["LIV", "CLB", "SHK", "STU"], "a": ["RMA", "DOR", "FEY", "SLB"]},
    "MCI": {"pot": 1, "h": ["PSG", "SPO", "NAP", "AEK"], "a": ["BAR", "POR", "RBL", "LEN"]},
    "ARS": {"pot": 1, "h": ["RMA", "DOR", "LIL", "SAB"], "a": ["BAY", "BET", "NAP", "SLA"]},
    "BAR": {"pot": 1, "h": ["MCI", "AVL", "FEY", "COM"], "a": ["PSG", "SPO", "GAL", "SAB"]},
    "ATM": {"pot": 1, "h": ["BAY", "MUN", "FEN", "VIK"], "a": ["LIV", "PSV", "BOD", "STU"]},

    # ── Pot 2 ────────────────────────────────────────────────────────────────
    "DOR": {"pot": 2, "h": ["INT", "BET", "VIL", "AEK"], "a": ["ARS", "AVL", "BOD", "SAB"]},
    "ROM": {"pot": 2, "h": ["RMA", "SPO", "LIL", "SLB"], "a": ["PSG", "MUN", "FEN", "AEK"]},
    "SPO": {"pot": 2, "h": ["BAR", "MUN", "GAL", "LSK"], "a": ["MCI", "ROM", "SHK", "LEN"]},
    "AVL": {"pot": 2, "h": ["PSG", "DOR", "FEN", "VIK"], "a": ["BAR", "CLB", "GAL", "SLA"]},
    "POR": {"pot": 2, "h": ["MCI", "PSV", "NAP", "SLA"], "a": ["LIV", "BET", "FEY", "LSK"]},
    "MUN": {"pot": 2, "h": ["BAY", "ROM", "RBL", "SAB"], "a": ["ATM", "SPO", "VIL", "COM"]},
    "CLB": {"pot": 2, "h": ["LIV", "AVL", "BOD", "LEN"], "a": ["INT", "PSV", "NAP", "STU"]},
    "BET": {"pot": 2, "h": ["ARS", "POR", "FEY", "COM"], "a": ["BAY", "DOR", "LIL", "SLB"]},
    "PSV": {"pot": 2, "h": ["ATM", "CLB", "SHK", "STU"], "a": ["RMA", "POR", "RBL", "VIK"]},

    # ── Pot 3 ────────────────────────────────────────────────────────────────
    "FEY": {"pot": 3, "h": ["INT", "POR", "RBL", "COM"], "a": ["BAR", "BET", "GAL", "VIK"]},
    "LIL": {"pot": 3, "h": ["BAY", "BET", "GAL", "SLB"], "a": ["ARS", "ROM", "BOD", "STU"]},
    "BOD": {"pot": 3, "h": ["ATM", "DOR", "LIL", "LSK"], "a": ["BAY", "CLB", "NAP", "LEN"]},
    "NAP": {"pot": 3, "h": ["ARS", "CLB", "BOD", "VIK"], "a": ["MCI", "POR", "VIL", "SAB"]},
    "RBL": {"pot": 3, "h": ["MCI", "PSV", "SHK", "LEN"], "a": ["RMA", "MUN", "FEY", "COM"]},
    "VIL": {"pot": 3, "h": ["PSG", "MUN", "NAP", "SAB"], "a": ["LIV", "DOR", "FEN", "SLA"]},
    "FEN": {"pot": 3, "h": ["LIV", "ROM", "VIL", "SLA"], "a": ["ATM", "AVL", "SHK", "LSK"]},
    "SHK": {"pot": 3, "h": ["RMA", "SPO", "FEN", "AEK"], "a": ["INT", "PSV", "RBL", "SLB"]},
    "GAL": {"pot": 3, "h": ["BAR", "AVL", "FEY", "STU"], "a": ["PSG", "SPO", "LIL", "AEK"]},

    # ── Pot 4 ────────────────────────────────────────────────────────────────
    "SLA": {"pot": 4, "h": ["ARS", "AVL", "VIL", "LEN"], "a": ["BAY", "POR", "FEN", "SAB"]},
    "SLB": {"pot": 4, "h": ["INT", "BET", "SHK", "STU"], "a": ["PSG", "ROM", "LIL", "LSK"]},
    "STU": {"pot": 4, "h": ["ATM", "CLB", "LIL", "VIK"], "a": ["INT", "PSV", "GAL", "SLB"]},
    "AEK": {"pot": 4, "h": ["RMA", "ROM", "GAL", "LSK"], "a": ["MCI", "DOR", "SHK", "COM"]},
    "LSK": {"pot": 4, "h": ["LIV", "POR", "FEN", "SLB"], "a": ["RMA", "SPO", "BOD", "AEK"]},
    "COM": {"pot": 4, "h": ["PSG", "MUN", "RBL", "AEK"], "a": ["BAR", "BET", "FEY", "LEN"]},
    "LEN": {"pot": 4, "h": ["MCI", "SPO", "BOD", "COM"], "a": ["LIV", "CLB", "RBL", "SLA"]},
    "VIK": {"pot": 4, "h": ["BAY", "PSV", "FEY", "SAB"], "a": ["ATM", "AVL", "NAP", "STU"]},
    "SAB": {"pot": 4, "h": ["BAR", "DOR", "NAP", "SLA"], "a": ["ARS", "MUN", "VIL", "VIK"]},
}

# Strength of schedule published alongside the draw (football-md.com): average
# opponent Elo relative to the field, 100k sims. Used only as an independent
# cross-check on our own club ratings — positive = harder draw.
SOS_REFERENCE = {
    "SAB": 42, "MCI": 39, "LEN": 33, "CLB": 26, "COM": 25, "MUN": 16,
    "BOD": 13, "ATM": 13, "SLA": 12, "PSG": 12, "BAY": 11, "VIL": 11,
    "FEY": 11, "ARS": 7, "GAL": 7, "AVL": 5, "NAP": 3, "LIL": 3,
    "SPO": 0, "DOR": -1, "RBL": -2, "PSV": -6, "ROM": -8, "BAR": -9,
    "LIV": -9, "AEK": -10, "BET": -14, "VIK": -16, "SLB": -17, "POR": -18,
    "FEN": -18, "LSK": -21, "SHK": -28, "RMA": -28, "INT": -36, "STU": -48,
}
