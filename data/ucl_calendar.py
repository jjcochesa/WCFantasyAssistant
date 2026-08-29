"""
UEFA Champions League 2026-27 league-phase calendar.

Transcribed from the official matchday schedule graphics. Each entry lists the
matchday's playing dates and its 18 fixtures as (home, away) club codes.

scripts/build_calendar.py checks this against the already-validated draw in
data/ucl_draw.py: every fixture here must exist there with the same home/away,
each club must appear exactly once per matchday, and the 144 draw ties must be
used exactly once across the eight matchdays. That cross-check is what makes a
hand-transcription safe — a misread club name cannot satisfy all three.

Kick-offs are 18:45 or 21:00 CET; the model doesn't use kick-off time, so only
dates are recorded.
"""

# Matchday -> playing dates (CET)
DATES = {
    1: ["2026-09-08", "2026-09-09", "2026-09-10"],
    2: ["2026-10-13", "2026-10-14"],
    3: ["2026-10-20", "2026-10-21"],
    4: ["2026-11-03", "2026-11-04"],
    5: ["2026-11-24", "2026-11-25"],
    6: ["2026-12-08", "2026-12-09"],
    7: ["2027-01-19", "2027-01-20"],
    8: ["2027-01-27"],
}

# Matchday -> [(home, away), ...]
FIXTURES = {
    1: [
        # Tue 8 Sep
        ("AEK", "LSK"), ("CLB", "AVL"), ("DOR", "VIL"), ("POR", "MCI"),
        ("LIL", "BET"), ("RMA", "INT"),
        # Wed 9 Sep
        ("BAR", "FEY"), ("STU", "VIK"), ("LIV", "ATM"), ("PSG", "SLB"),
        ("SPO", "GAL"), ("NAP", "ARS"),
        # Thu 10 Sep
        ("FEN", "ROM"), ("PSV", "SHK"), ("COM", "RBL"), ("BAY", "BOD"),
        ("MUN", "SAB"), ("SLA", "LEN"),
    ],
    2: [
        # Tue 13 Oct
        ("LEN", "SPO"), ("SAB", "SLA"), ("ARS", "LIL"), ("ATM", "MUN"),
        ("INT", "CLB"), ("GAL", "BAR"), ("RBL", "PSV"), ("VIK", "BAY"),
        ("VIL", "NAP"),
        # Wed 14 Oct
        ("FEY", "COM"), ("LSK", "LIV"), ("ROM", "RMA"), ("AVL", "FEN"),
        ("SHK", "AEK"), ("BOD", "DOR"), ("MCI", "PSG"), ("BET", "POR"),
        ("SLB", "STU"),
    ],
    3: [
        # Tue 20 Oct
        ("FEN", "SLA"), ("SAB", "DOR"), ("ROM", "SLB"), ("POR", "PSV"),
        ("LIV", "VIL"), ("MCI", "AEK"), ("PSG", "BAR"), ("NAP", "BOD"),
        ("STU", "ATM"),
        # Wed 21 Oct
        ("COM", "MUN"), ("LIL", "GAL"), ("AVL", "VIK"), ("CLB", "LEN"),
        ("BAY", "ARS"), ("INT", "SHK"), ("RMA", "RBL"), ("BET", "FEY"),
        ("SPO", "LSK"),
    ],
    4: [
        # Tue 3 Nov
        ("SHK", "SPO"), ("GAL", "STU"), ("ATM", "BAY"), ("BAR", "AVL"),
        ("FEY", "INT"), ("BOD", "LIL"), ("LSK", "SLB"), ("MUN", "ROM"),
        ("VIL", "PSG"),
        # Wed 4 Nov
        ("AEK", "RMA"), ("FEN", "LIV"), ("DOR", "BET"), ("POR", "NAP"),
        ("PSV", "CLB"), ("RBL", "MCI"), ("LEN", "COM"), ("SLA", "ARS"),
        ("VIK", "SAB"),
    ],
    5: [
        # Tue 24 Nov
        ("BOD", "LSK"), ("GAL", "AVL"), ("ARS", "DOR"), ("COM", "AEK"),
        ("FEY", "POR"), ("MCI", "NAP"), ("RBL", "LEN"), ("RMA", "PSV"),
        ("SLB", "BET"),
        # Wed 25 Nov
        ("SAB", "BAR"), ("SLA", "VIL"), ("ATM", "VIK"), ("CLB", "LIV"),
        ("INT", "STU"), ("SHK", "FEN"), ("LIL", "BAY"), ("PSG", "ROM"),
        ("SPO", "MUN"),
    ],
    6: [
        # Tue 8 Dec
        ("VIK", "FEY"), ("VIL", "SAB"), ("AEK", "GAL"), ("ROM", "SPO"),
        ("AVL", "PSG"), ("BAR", "MCI"), ("BAY", "SLA"), ("MUN", "RBL"),
        ("NAP", "CLB"),
        # Wed 9 Dec
        ("BET", "COM"), ("SLB", "SHK"), ("ARS", "RMA"), ("DOR", "INT"),
        ("LSK", "FEN"), ("LIV", "POR"), ("PSV", "ATM"), ("LEN", "BOD"),
        ("STU", "LIL"),
    ],
    7: [
        # Tue 19 Jan
        ("BOD", "ATM"), ("GAL", "FEY"), ("AEK", "ROM"), ("AVL", "DOR"),
        ("INT", "LIV"), ("POR", "SLA"), ("LIL", "SLB"), ("RMA", "LSK"),
        ("STU", "CLB"),
        # Wed 20 Jan
        ("FEN", "VIL"), ("SAB", "NAP"), ("COM", "PSG"), ("MUN", "BAY"),
        ("RBL", "SHK"), ("LEN", "MCI"), ("BET", "ARS"), ("SPO", "BAR"),
        ("VIK", "PSV"),
    ],
    8: [
        # Wed 27 Jan — all 18 kick off simultaneously
        ("ARS", "SAB"), ("ROM", "LIL"), ("ATM", "FEN"), ("DOR", "AEK"),
        ("CLB", "BOD"), ("BAY", "BET"), ("BAR", "COM"), ("SHK", "RMA"),
        ("FEY", "RBL"), ("LSK", "POR"), ("LIV", "LEN"), ("MCI", "SPO"),
        ("PSG", "GAL"), ("PSV", "STU"), ("SLA", "AVL"), ("NAP", "VIK"),
        ("VIL", "MUN"), ("SLB", "INT"),
    ],
}
