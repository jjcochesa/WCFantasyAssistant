"""
Team-level data for the UEFA Champions League Fantasy assistant.

Data is keyed BY MATCHDAY so squads can be optimised over a horizon (e.g. "best
team for MD1-MD3" before a Wildcard) rather than one round at a time. The
single-round dicts the engine imports (FIXTURES / PROJ_GOALS / CS_PCT / FDR) are
derived views of CURRENT_MD, so there is one source of truth.
Stages: MD1 … MD8 → PO → R16 → QF → SF → Final.

Sources:
  - Projected goals & CS%: bookmaker-derived boards (FPLJoe-style) or
    scripts/build_r32.py (odds → de-vig → Poisson lambdas)
  - FDR (1=easiest, 5=hardest): opponent threat = avg(opp_xGF, opp_CS%),
    banded into 5 tiers
  - QUAL_PROBS: Monte-Carlo — scripts/build_league_phase.py for the league
    phase, bracket sim for the knockouts
  - Fixtures from the official UEFA calendar

STATUS: league-phase draw is in (27.08.26) — 36 clubs, pots, 144 fixtures and
qualification probabilities are loaded. Still awaiting UEFA's matchday calendar,
so the per-matchday SCHEDULE/goals/CS%/FDR dicts stay empty and the app shows an
'awaiting data' banner for the upcoming round.
"""

import math as _math

# ── Competition calendar ──────────────────────────────────────────────────────

# Label for the round currently being projected (display only)
CURRENT_ROUND = "MD1"
CURRENT_ROUND_DATE = "08.09.26"   # MD1 deadline 18:45 CET (constraints_90.json)

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

# The 36 clubs in the 2026-27 league phase, grouped by draw pot.
TEAM_NAMES = {
    "PSG": "Paris Saint-Germain", "BAY": "Bayern München", "RMA": "Real Madrid", "LIV": "Liverpool", "INT": "Inter", "MCI": "Manchester City", "ARS": "Arsenal", "BAR": "Barcelona", "ATM": "Atlético Madrid",
    "DOR": "Borussia Dortmund", "ROM": "Roma", "SPO": "Sporting CP", "AVL": "Aston Villa", "POR": "Porto", "MUN": "Manchester United", "CLB": "Club Brugge", "BET": "Real Betis", "PSV": "PSV",
    "FEY": "Feyenoord", "LIL": "Lille", "BOD": "Bodø/Glimt", "NAP": "Napoli", "RBL": "RB Leipzig", "VIL": "Villarreal", "FEN": "Fenerbahçe", "SHK": "Shakhtar Donetsk", "GAL": "Galatasaray",
    "SLA": "Slavia Praha", "SLB": "Slovan Bratislava", "STU": "VfB Stuttgart", "AEK": "AEK Athens", "LSK": "LASK", "COM": "Como", "LEN": "Lens", "VIK": "Viking", "SAB": "Sabah",
}

# Draw pots (1-4). Filled at the draw — used for the "pot" label in the UI and
# as a coarse strength prior before any results exist.
POTS: dict[int, list[str]] = {
    1: ["PSG", "BAY", "RMA", "LIV", "INT", "MCI", "ARS", "BAR", "ATM"],
    2: ["DOR", "ROM", "SPO", "AVL", "POR", "MUN", "CLB", "BET", "PSV"],
    3: ["FEY", "LIL", "BOD", "NAP", "RBL", "VIL", "FEN", "SHK", "GAL"],
    4: ["SLA", "SLB", "STU", "AEK", "LSK", "COM", "LEN", "VIK", "SAB"],
}


# ── Per-matchday data ─────────────────────────────────────────────────────────
#
# The league phase is planned over a HORIZON (e.g. "best squad for MD1-MD3"),
# not one round at a time, so everything is keyed by matchday number. The
# single-round dicts further down are derived views of the current matchday, so
# there is one source of truth.
#
#   SCHEDULE[md][club]        -> opponent club code
#   HOME[md]                  -> set of clubs playing at home that matchday
#   PROJ_GOALS_BY_MD[md][club], CS_PCT_BY_MD[md][club], FDR_BY_MD[md][club]

CURRENT_MD = 1   # which league matchday CURRENT_ROUND refers to

SCHEDULE: dict[int, dict[str, str]] = {}
HOME: dict[int, set] = {}
PROJ_GOALS_BY_MD: dict[int, dict[str, float]] = {}
CS_PCT_BY_MD: dict[int, dict[str, float]] = {}
# FDR banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR_BY_MD: dict[int, dict[str, int]] = {}


def available_matchdays() -> list:
    """Matchdays that have both a schedule and projections loaded."""
    return sorted(md for md in SCHEDULE
                  if SCHEDULE.get(md) and PROJ_GOALS_BY_MD.get(md))


def has_md_data(md: int) -> bool:
    return bool(SCHEDULE.get(md)) and bool(PROJ_GOALS_BY_MD.get(md))


def get_md_fixture(md: int, team_code: str) -> str:
    """Opponent for this club on this matchday, or '' if it isn't playing."""
    return SCHEDULE.get(md, {}).get(team_code, "")


def get_md_proj(md: int, team_code: str) -> tuple:
    """(team_xg, cs_pct) for this club on this matchday."""
    return (PROJ_GOALS_BY_MD.get(md, {}).get(team_code, 1.0),
            CS_PCT_BY_MD.get(md, {}).get(team_code, 0.3))


def get_md_opponent_xg(md: int, team_code: str) -> float:
    """Opponent xG implied by this club's clean-sheet odds: λ = -ln(CS%)."""
    cs = CS_PCT_BY_MD.get(md, {}).get(team_code, 0.3)
    return -_math.log(max(cs, 0.01))


def get_md_fdr(md: int, team_code: str) -> int:
    return FDR_BY_MD.get(md, {}).get(team_code, 3)


def is_home(md: int, team_code: str) -> bool:
    return team_code in HOME.get(md, set())


# ── Single-round views (derived from CURRENT_MD; the engine imports these) ─────

FIXTURES: dict[str, str] = dict(SCHEDULE.get(CURRENT_MD, {}))
PROJ_GOALS: dict[str, float] = dict(PROJ_GOALS_BY_MD.get(CURRENT_MD, {}))
CS_PCT: dict[str, float] = dict(CS_PCT_BY_MD.get(CURRENT_MD, {}))
FDR: dict[str, int] = dict(FDR_BY_MD.get(CURRENT_MD, {}))

# Reach-probabilities per club (0.0–1.0):
#   top8 = finish 1-8 (direct to R16)   po = finish 9-24 (playoff)
#   r16 / qf / sf / f = reach that round
QUAL_PROBS: dict[str, dict] = {
    "BAR": {"top8": 0.7836, "po": 0.2141, "r16": 0.9738, "qf": 0.7506, "sf": 0.4701, "f": 0.2679},
    "RMA": {"top8": 0.7812, "po": 0.2164, "r16": 0.9714, "qf": 0.723, "sf": 0.4269, "f": 0.2309},
    "BAY": {"top8": 0.7546, "po": 0.2412, "r16": 0.9705, "qf": 0.7525, "sf": 0.4769, "f": 0.2794},
    "ARS": {"top8": 0.7104, "po": 0.2851, "r16": 0.9631, "qf": 0.7344, "sf": 0.4597, "f": 0.266},
    "PSG": {"top8": 0.6979, "po": 0.296, "r16": 0.9624, "qf": 0.7369, "sf": 0.4675, "f": 0.2765},
    "LIV": {"top8": 0.6838, "po": 0.309, "r16": 0.9417, "qf": 0.646, "sf": 0.3467, "f": 0.1678},
    "MCI": {"top8": 0.6265, "po": 0.3635, "r16": 0.9434, "qf": 0.6889, "sf": 0.4261, "f": 0.238},
    "INT": {"top8": 0.6226, "po": 0.3683, "r16": 0.9123, "qf": 0.5576, "sf": 0.2554, "f": 0.1014},
    "ATM": {"top8": 0.4086, "po": 0.5515, "r16": 0.8231, "qf": 0.4398, "sf": 0.1925, "f": 0.0739},
    "NAP": {"top8": 0.2257, "po": 0.671, "r16": 0.6353, "qf": 0.2368, "sf": 0.0701, "f": 0.017},
    "MUN": {"top8": 0.2095, "po": 0.6651, "r16": 0.628, "qf": 0.2497, "sf": 0.0814, "f": 0.0219},
    "RBL": {"top8": 0.19, "po": 0.6821, "r16": 0.5842, "qf": 0.1941, "sf": 0.0536, "f": 0.0125},
    "AVL": {"top8": 0.1516, "po": 0.6775, "r16": 0.5211, "qf": 0.1555, "sf": 0.0394, "f": 0.0081},
    "ROM": {"top8": 0.1443, "po": 0.6973, "r16": 0.5144, "qf": 0.1466, "sf": 0.036, "f": 0.0071},
    "VIL": {"top8": 0.137, "po": 0.6771, "r16": 0.5111, "qf": 0.1591, "sf": 0.0413, "f": 0.008},
    "DOR": {"top8": 0.1158, "po": 0.6756, "r16": 0.4489, "qf": 0.1197, "sf": 0.0266, "f": 0.0043},
    "BET": {"top8": 0.1151, "po": 0.6803, "r16": 0.4357, "qf": 0.1032, "sf": 0.0219, "f": 0.0032},
    "SPO": {"top8": 0.0968, "po": 0.6659, "r16": 0.4068, "qf": 0.1016, "sf": 0.021, "f": 0.0034},
    "POR": {"top8": 0.0884, "po": 0.6556, "r16": 0.3616, "qf": 0.0749, "sf": 0.0137, "f": 0.0021},
    "BOD": {"top8": 0.0883, "po": 0.646, "r16": 0.3963, "qf": 0.0977, "sf": 0.0206, "f": 0.0037},
    "CLB": {"top8": 0.0871, "po": 0.6147, "r16": 0.3849, "qf": 0.094, "sf": 0.0218, "f": 0.0037},
    "STU": {"top8": 0.0602, "po": 0.5943, "r16": 0.2427, "qf": 0.0342, "sf": 0.0038, "f": 0.0003},
    "FEN": {"top8": 0.0514, "po": 0.568, "r16": 0.24, "qf": 0.0386, "sf": 0.0053, "f": 0.0006},
    "LIL": {"top8": 0.0438, "po": 0.5906, "r16": 0.2662, "qf": 0.0468, "sf": 0.0073, "f": 0.0007},
    "PSV": {"top8": 0.0284, "po": 0.4852, "r16": 0.1724, "qf": 0.0214, "sf": 0.0026, "f": 0.0002},
    "GAL": {"top8": 0.0275, "po": 0.4991, "r16": 0.1875, "qf": 0.0277, "sf": 0.0039, "f": 0.0003},
    "COM": {"top8": 0.0247, "po": 0.4587, "r16": 0.1738, "qf": 0.0275, "sf": 0.0035, "f": 0.0003},
    "LEN": {"top8": 0.0202, "po": 0.4258, "r16": 0.1584, "qf": 0.0236, "sf": 0.0032, "f": 0.0005},
    "SHK": {"top8": 0.0059, "po": 0.2919, "r16": 0.0516, "qf": 0.0029, "sf": 0.0002, "f": 0.0},
    "SLA": {"top8": 0.0052, "po": 0.2692, "r16": 0.0579, "qf": 0.0046, "sf": 0.0003, "f": 0.0},
    "FEY": {"top8": 0.0049, "po": 0.2572, "r16": 0.0556, "qf": 0.0048, "sf": 0.0003, "f": 0.0},
    "AEK": {"top8": 0.0042, "po": 0.2551, "r16": 0.0434, "qf": 0.0029, "sf": 0.0001, "f": 0.0},
    "VIK": {"top8": 0.0038, "po": 0.2702, "r16": 0.047, "qf": 0.0023, "sf": 0.0002, "f": 0.0},
    "LSK": {"top8": 0.0009, "po": 0.1201, "r16": 0.0108, "qf": 0.0002, "sf": 0.0, "f": 0.0},
    "SLB": {"top8": 0.0001, "po": 0.0418, "r16": 0.0017, "qf": 0.0, "sf": 0.0, "f": 0.0},
    "SAB": {"top8": 0.0, "po": 0.0195, "r16": 0.0009, "qf": 0.0, "sf": 0.0, "f": 0.0},
}

# Expected REMAINING matches per club, from the same Monte-Carlo. Counts both
# legs of two-legged ties, so it is NOT just the sum of the reach-probabilities.
EXP_GAMES: dict[str, float] = {
    "PSG": 13.202,
    "BAY": 13.162,
    "ARS": 13.151,
    "BAR": 13.085,
    "MCI": 13.082,
    "RMA": 12.906,
    "LIV": 12.654,
    "INT": 12.288,
    "ATM": 12.088,
    "MUN": 11.27,
    "NAP": 11.243,
    "RBL": 11.041,
    "ROM": 10.796,
    "AVL": 10.795,
    "VIL": 10.785,
    "DOR": 10.546,
    "BET": 10.486,
    "SPO": 10.394,
    "BOD": 10.325,
    "CLB": 10.234,
    "POR": 10.214,
    "LIL": 9.823,
    "STU": 9.75,
    "FEN": 9.704,
    "GAL": 9.437,
    "PSV": 9.363,
    "COM": 9.327,
    "LEN": 9.222,
    "SHK": 8.693,
    "SLA": 8.664,
    "VIK": 8.639,
    "FEY": 8.636,
    "AEK": 8.603,
    "LSK": 8.262,
    "SLB": 8.087,
    "SAB": 8.041,
}

_EMPTY_QUAL = {"top8": 0.0, "po": 0.0, "r16": 0.0, "qf": 0.0, "sf": 0.0, "f": 0.0}


def has_round_data() -> bool:
    """True once the upcoming round's team data has been loaded."""
    return bool(PROJ_GOALS) and bool(FIXTURES)


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
