"""
Team-level data for the UEFA Champions League Fantasy assistant.

One round at a time: we fill the dicts below for the upcoming matchday, the app
projects it, then we wipe and refresh for the next one
(MD1 … MD8 → PO → R16 → QF → SF → Final).

Sources:
  - Projected goals & CS%: bookmaker-derived boards (FPLJoe-style) or
    scripts/build_r32.py (odds → de-vig → Poisson lambdas)
  - FDR (1=easiest, 5=hardest): opponent threat = avg(opp_xGF, opp_CS%),
    banded into 5 tiers
  - QUAL_PROBS: Monte-Carlo — scripts/build_league_phase.py for the league
    phase, bracket sim for the knockouts
  - Fixtures from the official UEFA calendar

STATUS: awaiting the 2026-27 league-phase draw (late August). The team dicts are
intentionally empty — the app shows an "awaiting draw" state until they're
filled. Nothing here is World Cup data any more; that lives in git history.
"""

# ── Competition calendar ──────────────────────────────────────────────────────

# Label for the round currently being projected (display only)
CURRENT_ROUND = "MD1"
CURRENT_ROUND_DATE = "TBC"

LEAGUE_MATCHDAYS = 8          # single 36-team league table, 8 games each
LEAGUE_TEAMS = 36

# Every stage in order. The league phase is a single table; from PO onward it's
# a bracket.
STAGES = ["MD1", "MD2", "MD3", "MD4", "MD5", "MD6", "MD7", "MD8",
          "PO", "R16", "QF", "SF", "F"]

# Two-legged ties — each is TWO fantasy matchdays, which doubles the scoring
# opportunities for teams that reach them (matters for EXP_GAMES / Tourn xPts).
TWO_LEGGED = {"PO", "R16", "QF", "SF"}

# League-phase finishing positions → what they earn
QUALIFY_DIRECT_R16 = (1, 8)    # positions 1-8 skip the playoff
QUALIFY_PLAYOFF    = (9, 24)   # positions 9-24 play the two-legged playoff
ELIMINATED_FROM    = 25        # 25-36 are out


def stage_legs(stage: str) -> int:
    """How many matches a team plays in this stage (2 for two-legged ties)."""
    return 2 if stage in TWO_LEGGED else 1


def is_league_phase(stage: str = None) -> bool:
    return (stage or CURRENT_ROUND).startswith("MD")


# ── Clubs ─────────────────────────────────────────────────────────────────────

# Reference pool of club codes → names. This is a superset of likely
# participants so the codes are stable across seasons; prune to the actual 36
# once the draw is made.
TEAM_NAMES = {
    # England
    "MCI": "Manchester City", "LIV": "Liverpool", "ARS": "Arsenal",
    "CHE": "Chelsea", "TOT": "Tottenham", "NEW": "Newcastle", "AVL": "Aston Villa",
    # Spain
    "RMA": "Real Madrid", "BAR": "Barcelona", "ATM": "Atlético Madrid",
    "ATH": "Athletic Club", "VIL": "Villarreal", "BET": "Real Betis",
    # Germany
    "BAY": "Bayern München", "DOR": "Borussia Dortmund", "LEV": "Bayer Leverkusen",
    "RBL": "RB Leipzig", "STU": "Stuttgart", "FRA": "Eintracht Frankfurt",
    # Italy
    "INT": "Inter", "MIL": "AC Milan", "JUV": "Juventus", "NAP": "Napoli",
    "ATA": "Atalanta", "ROM": "Roma",
    # France
    "PSG": "Paris Saint-Germain", "MON": "Monaco", "MAR": "Marseille",
    "LIL": "Lille", "LYO": "Lyon",
    # Portugal / Netherlands / Belgium
    "BEN": "Benfica", "POR": "Porto", "SPO": "Sporting CP",
    "AJA": "Ajax", "PSV": "PSV", "FEY": "Feyenoord", "CLB": "Club Brugge",
    # Rest of Europe
    "CEL": "Celtic", "GAL": "Galatasaray", "FEN": "Fenerbahçe",
    "RBS": "RB Salzburg", "SHK": "Shakhtar Donetsk", "SLP": "Slavia Praha",
    "DZG": "Dinamo Zagreb", "OLY": "Olympiacos", "STE": "Sturm Graz",
    "BSC": "Young Boys", "COP": "Copenhagen", "BOD": "Bodø/Glimt",
}

# Draw pots (1-4). Filled at the draw — used for the "pot" label in the UI and
# as a coarse strength prior before any results exist.
POTS: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}


# ── Per-round data (filled each matchday) ─────────────────────────────────────

# Next opponent (club code) for the upcoming round
FIXTURES: dict[str, str] = {}

# Projected goals for the upcoming match
PROJ_GOALS: dict[str, float] = {}

# Clean sheet probability for the upcoming match
CS_PCT: dict[str, float] = {}

# FDR for the upcoming match (1=easiest, 5=hardest)
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR: dict[str, int] = {}

# Reach-probabilities per club (0.0–1.0):
#   top8 = finish 1-8 (direct to R16)   po = finish 9-24 (playoff)
#   r16 / qf / sf / f = reach that round
QUAL_PROBS: dict[str, dict] = {}

# Expected REMAINING matches per club, from the same Monte-Carlo. Counts both
# legs of two-legged ties, so it is NOT just the sum of the reach-probabilities.
EXP_GAMES: dict[str, float] = {}

_EMPTY_QUAL = {"top8": 0.0, "po": 0.0, "r16": 0.0, "qf": 0.0, "sf": 0.0, "f": 0.0}


def has_round_data() -> bool:
    """True once the upcoming round's team data has been loaded."""
    return bool(PROJ_GOALS) and bool(FIXTURES)


import math as _math


def get_team_proj(team_code: str) -> tuple:
    """Returns (team_xg, cs_pct) for the upcoming match."""
    return (PROJ_GOALS.get(team_code, 1.0), CS_PCT.get(team_code, 0.3))


def get_team_xg(team_code: str) -> float:
    return PROJ_GOALS.get(team_code, 1.0)


def get_team_cs(team_code: str) -> float:
    return CS_PCT.get(team_code, 0.3)


def get_opponent_xg(team_code: str) -> float:
    """Estimate opponent xG from cs_pct via Poisson: P(CS) = e^(-λ) → λ = -ln(cs_pct)."""
    cs_pct = get_team_cs(team_code)
    return -_math.log(max(cs_pct, 0.01))


def get_team_fdr(team_code: str) -> int:
    """FDR for the upcoming match. Lower = easier."""
    return FDR.get(team_code, 3)


def get_next_opponent(team_code: str) -> str:
    return FIXTURES.get(team_code, "?")


def get_team_pot(team_code: str) -> int:
    for pot, teams in POTS.items():
        if team_code in teams:
            return pot
    return 0


def get_group_balance(team_code: str) -> str:
    """Draw pot label — the UCL analogue of the WC group-strength tag.
    (Name kept for engine compatibility.)"""
    pot = get_team_pot(team_code)
    return f"Pot {pot}" if pot else "Unknown"


def get_qual_probs(team_code: str) -> dict:
    """Returns {top8, po, r16, qf, sf, f} reach-probabilities (0.0–1.0)."""
    return QUAL_PROBS.get(team_code, dict(_EMPTY_QUAL))


def get_expected_games(team_code: str) -> float:
    """Expected number of REMAINING matches (both legs counted for two-legged
    ties). Prefers the Monte-Carlo EXP_GAMES; falls back to a leg-weighted sum
    of the reach-probabilities for any club not in that table."""
    if team_code in EXP_GAMES:
        return EXP_GAMES[team_code]
    p = get_qual_probs(team_code)
    return round(p["po"] * 2 + p["r16"] * 2 + p["qf"] * 2 + p["sf"] * 2 + p["f"], 3)
