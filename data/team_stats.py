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
CURRENT_ROUND = "R32"
CURRENT_ROUND_DATE = "28.06.26"

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

# Next opponent (3-letter code) — Round of 32 (the 16 locked knockout matches)
FIXTURES = {
    "RSA": "CAN", "CAN": "RSA",   # Sun 28.06
    "GER": "PAR", "PAR": "GER",   # Mon 29.06
    "BRA": "JPN", "JPN": "BRA",   # Mon 29.06
    "NED": "MAR", "MAR": "NED",   # Mon 29.06
    "CIV": "NOR", "NOR": "CIV",   # Tue 30.06
    "FRA": "SWE", "SWE": "FRA",   # Tue 30.06
    "MEX": "ECU", "ECU": "MEX",   # Tue 30.06
    "ENG": "COD", "COD": "ENG",   # Wed 01.07
    "BEL": "SEN", "SEN": "BEL",   # Wed 01.07
    "USA": "BIH", "BIH": "USA",   # Wed 01.07
    "ESP": "AUT", "AUT": "ESP",   # Thu 02.07
    "POR": "CRO", "CRO": "POR",   # Thu 02.07
    "SUI": "ALG", "ALG": "SUI",   # Thu 02.07
    "ARG": "CPV", "CPV": "ARG",   # Fri 03.07
    "AUS": "EGY", "EGY": "AUS",   # Fri 03.07
    "COL": "GHA", "GHA": "COL",   # Fri 03.07
}

# Projected goals for the R32 match — FPLJoe.com R32 (SBOBET & Betfair, 28.06.26)
# The 32 qualified teams direct.
PROJ_GOALS = {
    "GER": 2.26, "PAR": 0.67, "FRA": 2.53, "SWE": 0.74, "RSA": 0.75, "CAN": 1.63,
    "NED": 1.40, "MAR": 0.99, "POR": 1.54, "CRO": 0.89, "ESP": 2.14, "AUT": 0.53,
    "USA": 2.14, "BIH": 0.65, "BEL": 1.35, "SEN": 0.99, "BRA": 1.72, "JPN": 0.90,
    "CIV": 1.15, "NOR": 1.59, "MEX": 1.21, "ECU": 0.85, "ENG": 2.20, "COD": 0.48,
    "ARG": 2.59, "CPV": 0.42, "AUS": 0.96, "EGY": 1.10, "SUI": 1.59, "ALG": 1.00,
    "COL": 1.64, "GHA": 0.67,
}

# Clean sheet probability for the R32 match — FPLJoe.com R32 (SBOBET & Betfair)
# The 32 qualified teams direct.
CS_PCT = {
    "GER": 0.51, "PAR": 0.10, "FRA": 0.48, "SWE": 0.08, "RSA": 0.19, "CAN": 0.47,
    "NED": 0.37, "MAR": 0.25, "POR": 0.41, "CRO": 0.21, "ESP": 0.59, "AUT": 0.12,
    "USA": 0.52, "BIH": 0.12, "BEL": 0.37, "SEN": 0.26, "BRA": 0.41, "JPN": 0.18,
    "CIV": 0.20, "NOR": 0.32, "MEX": 0.43, "ECU": 0.30, "ENG": 0.62, "COD": 0.11,
    "ARG": 0.66, "CPV": 0.08, "AUS": 0.33, "EGY": 0.38, "SUI": 0.37, "ALG": 0.20,
    "COL": 0.51, "GHA": 0.19,
}

# FDR for the R32 match (1=easiest, 5=hardest)
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR = {
    # 1 — easiest (facing very weak opponent)
    "GER": 1, "FRA": 1, "ESP": 1, "USA": 1, "ENG": 1, "ARG": 1, "COL": 1,
    # 2 — easy
    "CAN": 2, "POR": 2, "BRA": 2, "MEX": 2, "SUI": 2,
    # 3 — moderate
    "NED": 3, "BEL": 3, "NOR": 3, "ECU": 3, "AUS": 3, "EGY": 3,
    # 4 — hard
    "RSA": 4, "MAR": 4, "CRO": 4, "SEN": 4, "JPN": 4, "CIV": 4, "ALG": 4, "GHA": 4,
    # 5 — hardest (facing strong opponent)
    "PAR": 5, "SWE": 5, "AUT": 5, "BIH": 5, "COD": 5, "CPV": 5,
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

# Tournament qualification probabilities (0.0–1.0) per team — 200k Monte-Carlo of
# the locked R32 bracket. r32 = reaches last 32 (=1.0, all already qualified),
# r16 = reaches last 16, qf = quarters, sf = semis, f = reaches the final.
# R32 advance prob is exact (Poisson on the two FPLJoe lambdas); R16+ use a
# bookmaker-derived attack/defence proxy. INTERIM — swap for the Elo-based
# build_r32.py output (data/r32_output.json) when available.
QUAL_PROBS: dict[str, dict] = {
    "GER": {"r32": 1.0, "r16": 0.821, "qf": 0.441, "sf": 0.284, "f": 0.16},
    "PAR": {"r32": 1.0, "r16": 0.179, "qf": 0.041, "sf": 0.012, "f": 0.003},
    "FRA": {"r32": 1.0, "r16": 0.836, "qf": 0.481, "sf": 0.317, "f": 0.185},
    "SWE": {"r32": 1.0, "r16": 0.164, "qf": 0.037, "sf": 0.01, "f": 0.002},
    "RSA": {"r32": 1.0, "r16": 0.293, "qf": 0.113, "sf": 0.029, "f": 0.008},
    "CAN": {"r32": 1.0, "r16": 0.707, "qf": 0.422, "sf": 0.184, "f": 0.089},
    "NED": {"r32": 1.0, "r16": 0.599, "qf": 0.301, "sf": 0.115, "f": 0.049},
    "MAR": {"r32": 1.0, "r16": 0.401, "qf": 0.164, "sf": 0.049, "f": 0.017},
    "POR": {"r32": 1.0, "r16": 0.654, "qf": 0.291, "sf": 0.142, "f": 0.063},
    "CRO": {"r32": 1.0, "r16": 0.346, "qf": 0.105, "sf": 0.036, "f": 0.011},
    "ESP": {"r32": 1.0, "r16": 0.836, "qf": 0.554, "sf": 0.332, "f": 0.184},
    "AUT": {"r32": 1.0, "r16": 0.164, "qf": 0.049, "sf": 0.012, "f": 0.003},
    "USA": {"r32": 1.0, "r16": 0.81, "qf": 0.538, "sf": 0.302, "f": 0.162},
    "BIH": {"r32": 1.0, "r16": 0.19, "qf": 0.061, "sf": 0.015, "f": 0.003},
    "BEL": {"r32": 1.0, "r16": 0.59, "qf": 0.255, "sf": 0.11, "f": 0.045},
    "SEN": {"r32": 1.0, "r16": 0.41, "qf": 0.145, "sf": 0.051, "f": 0.017},
    "BRA": {"r32": 1.0, "r16": 0.684, "qf": 0.401, "sf": 0.192, "f": 0.087},
    "JPN": {"r32": 1.0, "r16": 0.316, "qf": 0.124, "sf": 0.037, "f": 0.011},
    "CIV": {"r32": 1.0, "r16": 0.4, "qf": 0.166, "sf": 0.057, "f": 0.018},
    "NOR": {"r32": 1.0, "r16": 0.6, "qf": 0.31, "sf": 0.136, "f": 0.057},
    "MEX": {"r32": 1.0, "r16": 0.592, "qf": 0.236, "sf": 0.119, "f": 0.048},
    "ECU": {"r32": 1.0, "r16": 0.408, "qf": 0.128, "sf": 0.054, "f": 0.017},
    "ENG": {"r32": 1.0, "r16": 0.853, "qf": 0.593, "sf": 0.392, "f": 0.22},
    "COD": {"r32": 1.0, "r16": 0.147, "qf": 0.042, "sf": 0.012, "f": 0.002},
    "ARG": {"r32": 1.0, "r16": 0.899, "qf": 0.668, "sf": 0.461, "f": 0.297},
    "CPV": {"r32": 1.0, "r16": 0.101, "qf": 0.026, "sf": 0.006, "f": 0.001},
    "AUS": {"r32": 1.0, "r16": 0.464, "qf": 0.134, "sf": 0.057, "f": 0.022},
    "EGY": {"r32": 1.0, "r16": 0.536, "qf": 0.172, "sf": 0.08, "f": 0.033},
    "SUI": {"r32": 1.0, "r16": 0.636, "qf": 0.329, "sf": 0.135, "f": 0.064},
    "ALG": {"r32": 1.0, "r16": 0.364, "qf": 0.138, "sf": 0.04, "f": 0.014},
    "COL": {"r32": 1.0, "r16": 0.73, "qf": 0.434, "sf": 0.197, "f": 0.101},
    "GHA": {"r32": 1.0, "r16": 0.27, "qf": 0.099, "sf": 0.025, "f": 0.007},
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
    """Sum of all stage probabilities = expected additional games beyond MD3."""
    p = get_qual_probs(team_code)
    return round(p["r32"] + p["r16"] + p["qf"] + p["sf"] + p["f"], 3)
