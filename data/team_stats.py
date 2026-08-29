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

STATUS: draw (27.08.26) and matchday calendar are both loaded — 36 clubs, pots,
144 dated fixtures, per-matchday goals/CS%/FDR and qualification probabilities.
The per-matchday numbers are Elo-derived until a bookmaker board is supplied;
rebuild them with scripts/build_md_projections.py --board <file>.
"""

import json as _json
import math as _math
import os as _os

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
MD_DATES: dict[int, list] = {}
MD_SOURCE: dict[int, str] = {}   # "model" (Elo-derived) or "board" (bookmaker)
# FDR banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR_BY_MD: dict[int, dict[str, int]] = {}


_MD_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                         "ucl_md_projections.json")


def _load_md_projections() -> None:
    """Fill the per-matchday dicts from data/ucl_md_projections.json.

    Built by scripts/build_md_projections.py — Elo-derived by default, or from a
    bookmaker board where one was supplied. Absent file just leaves the dicts
    empty and the app shows its awaiting-data banner.
    """
    if not _os.path.exists(_MD_FILE):
        return
    try:
        with open(_MD_FILE, encoding="utf-8") as f:
            blob = _json.load(f)
    except Exception:
        return
    for md_s, opp in (blob.get("schedule") or {}).items():
        SCHEDULE[int(md_s)] = dict(opp)
    for md_s, clubs in (blob.get("home") or {}).items():
        HOME[int(md_s)] = set(clubs)
    for md_s, vals in (blob.get("proj_goals") or {}).items():
        PROJ_GOALS_BY_MD[int(md_s)] = {k: float(v) for k, v in vals.items()}
    for md_s, vals in (blob.get("cs_pct") or {}).items():
        CS_PCT_BY_MD[int(md_s)] = {k: float(v) for k, v in vals.items()}
    for md_s, vals in (blob.get("fdr") or {}).items():
        FDR_BY_MD[int(md_s)] = {k: int(v) for k, v in vals.items()}
    for md_s, d in (blob.get("dates") or {}).items():
        MD_DATES[int(md_s)] = list(d)
    for md_s, src in (blob.get("source") or {}).items():
        MD_SOURCE[int(md_s)] = str(src)


_load_md_projections()


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


def set_current_matchday(md: int) -> None:
    """Point the single-round views at a different league matchday."""
    global CURRENT_MD, CURRENT_ROUND, CURRENT_ROUND_DATE
    CURRENT_MD = md
    CURRENT_ROUND = f"MD{md}"
    CURRENT_ROUND_DATE = (MD_DATES.get(md) or [""])[0]
    for target, src in ((FIXTURES, SCHEDULE), (PROJ_GOALS, PROJ_GOALS_BY_MD),
                        (CS_PCT, CS_PCT_BY_MD), (FDR, FDR_BY_MD)):
        target.clear()
        target.update(src.get(md, {}))

# Reach-probabilities per club (0.0–1.0):
#   top8 = finish 1-8 (direct to R16)   po = finish 9-24 (playoff)
#   r16 / qf / sf / f = reach that round
QUAL_PROBS: dict[str, dict] = {
    "RMA": {"top8": 0.6214, "po": 0.3465, "r16": 0.8815, "qf": 0.5928, "sf": 0.3559, "f": 0.1988},
    "BAR": {"top8": 0.6183, "po": 0.352, "r16": 0.8892, "qf": 0.6103, "sf": 0.3772, "f": 0.221},
    "BAY": {"top8": 0.5851, "po": 0.3756, "r16": 0.8772, "qf": 0.6097, "sf": 0.3853, "f": 0.2322},
    "PSG": {"top8": 0.5726, "po": 0.3861, "r16": 0.8693, "qf": 0.6041, "sf": 0.3862, "f": 0.2332},
    "ARS": {"top8": 0.5686, "po": 0.3942, "r16": 0.8725, "qf": 0.5997, "sf": 0.3792, "f": 0.2229},
    "LIV": {"top8": 0.5307, "po": 0.4134, "r16": 0.8306, "qf": 0.5273, "sf": 0.3, "f": 0.16},
    "INT": {"top8": 0.5048, "po": 0.4364, "r16": 0.8004, "qf": 0.4752, "sf": 0.2482, "f": 0.1205},
    "MCI": {"top8": 0.4951, "po": 0.4407, "r16": 0.8286, "qf": 0.5576, "sf": 0.3447, "f": 0.2011},
    "ATM": {"top8": 0.3676, "po": 0.5191, "r16": 0.7072, "qf": 0.3927, "sf": 0.1956, "f": 0.0896},
    "NAP": {"top8": 0.257, "po": 0.5625, "r16": 0.5809, "qf": 0.2658, "sf": 0.1106, "f": 0.0419},
    "MUN": {"top8": 0.246, "po": 0.5603, "r16": 0.5711, "qf": 0.2669, "sf": 0.1126, "f": 0.0423},
    "RBL": {"top8": 0.225, "po": 0.5614, "r16": 0.5292, "qf": 0.2274, "sf": 0.09, "f": 0.0306},
    "ROM": {"top8": 0.2045, "po": 0.5623, "r16": 0.4948, "qf": 0.1985, "sf": 0.0705, "f": 0.0224},
    "VIL": {"top8": 0.1968, "po": 0.5536, "r16": 0.487, "qf": 0.2041, "sf": 0.0777, "f": 0.0269},
    "AVL": {"top8": 0.1957, "po": 0.5568, "r16": 0.4882, "qf": 0.2018, "sf": 0.0744, "f": 0.0251},
    "DOR": {"top8": 0.1815, "po": 0.5538, "r16": 0.4533, "qf": 0.1729, "sf": 0.0596, "f": 0.0191},
    "BET": {"top8": 0.1719, "po": 0.5622, "r16": 0.4396, "qf": 0.1611, "sf": 0.0544, "f": 0.0152},
    "SPO": {"top8": 0.1592, "po": 0.5505, "r16": 0.4222, "qf": 0.1584, "sf": 0.0518, "f": 0.0155},
    "POR": {"top8": 0.154, "po": 0.539, "r16": 0.3939, "qf": 0.1353, "sf": 0.0396, "f": 0.0114},
    "BOD": {"top8": 0.1461, "po": 0.5469, "r16": 0.4133, "qf": 0.1521, "sf": 0.0507, "f": 0.0159},
    "CLB": {"top8": 0.1441, "po": 0.5271, "r16": 0.4003, "qf": 0.1553, "sf": 0.0545, "f": 0.0165},
    "STU": {"top8": 0.1237, "po": 0.5255, "r16": 0.3214, "qf": 0.0899, "sf": 0.0218, "f": 0.0048},
    "LIL": {"top8": 0.1096, "po": 0.5156, "r16": 0.327, "qf": 0.1061, "sf": 0.0307, "f": 0.0065},
    "FEN": {"top8": 0.1093, "po": 0.5087, "r16": 0.3088, "qf": 0.0904, "sf": 0.0235, "f": 0.0055},
    "GAL": {"top8": 0.0838, "po": 0.4801, "r16": 0.2668, "qf": 0.0759, "sf": 0.0199, "f": 0.0047},
    "PSV": {"top8": 0.0819, "po": 0.4738, "r16": 0.2562, "qf": 0.0699, "sf": 0.0176, "f": 0.0034},
    "COM": {"top8": 0.0755, "po": 0.4559, "r16": 0.2528, "qf": 0.0754, "sf": 0.0215, "f": 0.0056},
    "LEN": {"top8": 0.0688, "po": 0.4484, "r16": 0.2428, "qf": 0.0736, "sf": 0.0201, "f": 0.0045},
    "SHK": {"top8": 0.0389, "po": 0.3725, "r16": 0.1383, "qf": 0.0271, "sf": 0.0045, "f": 0.0008},
    "FEY": {"top8": 0.0364, "po": 0.346, "r16": 0.1395, "qf": 0.0308, "sf": 0.0052, "f": 0.0006},
    "VIK": {"top8": 0.0359, "po": 0.359, "r16": 0.1346, "qf": 0.026, "sf": 0.0046, "f": 0.0005},
    "SLA": {"top8": 0.0358, "po": 0.3613, "r16": 0.1443, "qf": 0.0305, "sf": 0.0059, "f": 0.0007},
    "AEK": {"top8": 0.0319, "po": 0.3472, "r16": 0.1256, "qf": 0.0224, "sf": 0.0043, "f": 0.0004},
    "LSK": {"top8": 0.0148, "po": 0.2472, "r16": 0.0654, "qf": 0.009, "sf": 0.0012, "f": 0.0},
    "SLB": {"top8": 0.0045, "po": 0.1447, "r16": 0.0243, "qf": 0.0014, "sf": 0.0001, "f": 0.0},
    "SAB": {"top8": 0.0034, "po": 0.1136, "r16": 0.022, "qf": 0.0026, "sf": 0.0003, "f": 0.0},
}

# Expected REMAINING matches per club, from the same Monte-Carlo. Counts both
# legs of two-legged ties, so it is NOT just the sum of the reach-probabilities.
EXP_GAMES: dict[str, float] = {
    "BAY": 12.728,
    "PSG": 12.725,
    "ARS": 12.714,
    "BAR": 12.678,
    "RMA": 12.552,
    "MCI": 12.544,
    "LIV": 12.303,
    "INT": 12.041,
    "ATM": 11.719,
    "NAP": 11.081,
    "MUN": 11.064,
    "RBL": 10.847,
    "ROM": 10.675,
    "VIL": 10.672,
    "AVL": 10.668,
    "DOR": 10.498,
    "BET": 10.45,
    "SPO": 10.381,
    "BOD": 10.342,
    "CLB": 10.291,
    "POR": 10.227,
    "LIL": 9.965,
    "STU": 9.922,
    "FEN": 9.868,
    "GAL": 9.69,
    "PSV": 9.639,
    "COM": 9.617,
    "LEN": 9.574,
    "SHK": 9.086,
    "SLA": 9.084,
    "VIK": 9.049,
    "FEY": 9.044,
    "AEK": 8.999,
    "LSK": 8.646,
    "SLB": 8.341,
    "SAB": 8.277,
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
