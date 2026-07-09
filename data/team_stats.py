"""
Hardcoded team-level data for WC 2026 — SINGLE upcoming match at a time.

From the group stage MD2 onward the model projects only the next round for each
team, then we wipe and refresh for the following round (MD2 → MD3 → R32 → R16 →
QF → SF → Final). Each round you send fresh CS% / xG and we swap the single
value per team below.

Sources:
  - Projected goals & CS% (R32): FPLJoe.com via SBOBET & Betfair Exchange markets
    (the 32 qualified teams direct — no Poisson derivation)
  - FDR (1=easiest, 5=hardest): derived from opponent threat = avg(opp_xGF, opp_CS%)
    banded into 5 tiers, consistent with FPLJoe PELE colour bands
  - QUAL_PROBS: 200k Monte-Carlo of the locked bracket. R32 advance prob is exact
    (Poisson on the two FPLJoe lambdas per match); R16+ use a bookmaker-derived
    attack/defence proxy. INTERIM — replace with the Elo-based build_r32.py output.
  - Fixtures from the official WC 2026 Round-of-32 bracket
"""

# Label for the round currently being projected (display only)
# Quarter-finals (MD6). All 4 QF matches are set — 8 teams left, no pending games.
CURRENT_ROUND = "QF"
CURRENT_ROUND_DATE = "09.07.26"

# Group assignments
GROUPS = {
    "A": ["MEX", "KOR", "CZE", "RSA"],
    "B": ["SUI", "CAN", "QAT", "BIH"],
    "C": ["BRA", "MAR", "SCO", "HAI"],
    "D": ["USA", "TUR", "AUS", "PAR"],
    "E": ["GER", "ECU", "CIV", "CUW"],
    "F": ["NED", "JPN", "SWE", "TUN"],
    "G": ["BEL", "IRN", "EGY", "NZL"],
    "H": ["ESP", "URU", "KSA", "CPV"],
    "I": ["FRA", "SEN", "NOR", "IRQ"],
    "J": ["ARG", "AUT", "ALG", "JOR"],
    "K": ["POR", "COL", "COD", "UZB"],
    "L": ["ENG", "CRO", "GHA", "PAN"],
}

# Full team name mapping
TEAM_NAMES = {
    "ESP": "Spain", "GER": "Germany", "BRA": "Brazil", "FRA": "France",
    "POR": "Portugal", "ENG": "England", "ARG": "Argentina", "BEL": "Belgium",
    "SUI": "Switzerland", "NED": "Netherlands", "MEX": "Mexico", "NOR": "Norway",
    "URU": "Uruguay", "COL": "Colombia", "AUT": "Austria", "USA": "USA",
    "CAN": "Canada", "ECU": "Ecuador", "MAR": "Morocco", "CRO": "Croatia",
    "TUR": "Turkey", "CIV": "Ivory Coast", "JPN": "Japan", "EGY": "Egypt",
    "SEN": "Senegal", "SCO": "Scotland", "CZE": "Czech Republic", "KOR": "South Korea",
    "SWE": "Sweden", "ALG": "Algeria", "PAR": "Paraguay", "IRN": "Iran",
    "BIH": "Bosnia-Herzegovina", "GHA": "Ghana", "AUS": "Australia", "RSA": "South Africa",
    "TUN": "Tunisia", "COD": "DR Congo", "UZB": "Uzbekistan", "PAN": "Panama",
    "KSA": "Saudi Arabia", "NZL": "New Zealand", "CPV": "Cape Verde",
    "QAT": "Qatar", "JOR": "Jordan", "HAI": "Haiti", "IRQ": "Iraq", "CUW": "Curacao",
}

# Next opponent (3-letter code) — Quarter-finals (the 4 locked matches).
FIXTURES = {
    "FRA": "MAR", "MAR": "FRA",   # Thu 09.07
    "ESP": "BEL", "BEL": "ESP",   # Fri 10.07
    "NOR": "ENG", "ENG": "NOR",   # Sat 11.07
    "ARG": "SUI", "SUI": "ARG",   # Sun 12.07
}

# Projected goals for the QF match — FPLJoe MD6 (09.07.26, deadline refresh). 8 QF teams.
PROJ_GOALS = {
    "FRA": 1.93, "MAR": 0.88, "ESP": 2.03, "BEL": 1.03,
    "NOR": 1.24, "ENG": 1.92, "ARG": 1.76, "SUI": 0.83,
}

# Clean sheet probability for the QF match — FPLJoe MD6.
CS_PCT = {
    "FRA": 0.43, "MAR": 0.13, "ESP": 0.37, "BEL": 0.12,
    "NOR": 0.15, "ENG": 0.31, "ARG": 0.45, "SUI": 0.16,
}

# FDR for the QF match (1=easiest, 5=hardest).
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR = {
    "FRA": 2, "MAR": 4, "ESP": 2, "BEL": 5,
    "NOR": 4, "ENG": 3, "ARG": 2, "SUI": 4,
}

# Group balance classification (from FIFA ranking analysis)
GROUP_BALANCE = {
    "D": "Most balanced",   # USA, Turkey, Australia, Paraguay
    "A": "Balanced",        # Mexico, South Korea, Czech Republic, South Africa
    "B": "Balanced",        # Switzerland, Canada, Qatar, Bosnia-Herzegovina
    "F": "Balanced",        # Netherlands, Japan, Sweden, Tunisia
    "K": "Medium",          # Portugal, Colombia, DR Congo, Uzbekistan
    "E": "Medium",          # Germany, Ecuador, Ivory Coast, Curacao
    "G": "Medium",          # Belgium, Iran, Egypt, New Zealand
    "I": "Medium",          # France, Senegal, Norway, Iraq
    "J": "Unbalanced",      # Argentina, Austria, Algeria, Jordan
    "L": "Unbalanced",      # England, Croatia, Panama, Ghana
    "C": "Unbalanced",      # Brazil, Morocco, Scotland, Haiti
    "H": "Most unbalanced", # Spain, Uruguay, Saudi Arabia, Cape Verde
}

# Tournament qualification probabilities (0.0–1.0) — reach-probabilities from a
# 400k Monte-Carlo of the QF→Final bracket. All 8 teams are in the QF (r32=r16=
# qf=1.0). QF matches use MD6 odds; SF + Final use the calibrated Elo
# (KO_VARIANCE_K). See EXP_GAMES for expected remaining matches.
QUAL_PROBS: dict[str, dict] = {
    "FRA": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.7262, "f": 0.3908},
    "MAR": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.2738, "f": 0.0946},
    "ESP": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.71, "f": 0.3896},
    "BEL": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.29, "f": 0.125},
    "NOR": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.3567, "f": 0.1199},
    "ENG": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.6433, "f": 0.3006},
    "ARG": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.7104, "f": 0.4536},
    "SUI": {"r32": 1.0, "r16": 1.0, "qf": 1.0, "sf": 0.2897, "f": 0.1259},
}

# Expected REMAINING matches per team from the same Monte-Carlo (next guaranteed
# game + every round they're simulated to advance to). Used for tournament_xpts
# instead of summing QUAL_PROBS, so already-played rounds aren't double-counted.
EXP_GAMES: dict[str, float] = {
    "FRA": 2.117, "MAR": 1.368, "ESP": 2.1, "BEL": 1.415,
    "NOR": 1.477, "ENG": 1.944, "ARG": 2.164, "SUI": 1.416,
}

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


def get_team_group(team_code: str) -> str:
    for grp, teams in GROUPS.items():
        if team_code in teams:
            return grp
    return "?"


def get_group_balance(team_code: str) -> str:
    grp = get_team_group(team_code)
    return GROUP_BALANCE.get(grp, "Unknown")


def get_qual_probs(team_code: str) -> dict:
    """Returns {r32, r16, qf, sf, f} qualification probabilities (0.0–1.0)."""
    return QUAL_PROBS.get(team_code, {"r32": 0.0, "r16": 0.0, "qf": 0.0, "sf": 0.0, "f": 0.0})


def get_expected_games(team_code: str) -> float:
    """Expected number of REMAINING matches (next guaranteed game + rounds the team
    is projected to advance to). Prefers the Monte-Carlo EXP_GAMES; falls back to
    summing reach-probabilities for any team not in that table."""
    if team_code in EXP_GAMES:
        return EXP_GAMES[team_code]
    p = get_qual_probs(team_code)
    return round(p["r32"] + p["r16"] + p["qf"] + p["sf"] + p["f"], 3)
