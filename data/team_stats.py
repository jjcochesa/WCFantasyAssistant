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

# Projected goals for the R32 match — build_r32.py (API-Football SBOBET/Betfair
# odds → de-vigged → Poisson lambdas). The 32 qualified teams.
PROJ_GOALS = {
    "RSA": 0.8, "CAN": 1.68, "GER": 2.18, "PAR": 0.72, "BRA": 1.72, "JPN": 0.88,
    "NED": 1.4, "MAR": 1.0, "CIV": 1.12, "NOR": 1.57, "FRA": 2.43, "SWE": 0.73,
    "MEX": 1.21, "ECU": 0.87, "ENG": 2.18, "COD": 0.57, "BEL": 1.37, "SEN": 0.96,
    "USA": 2.1, "BIH": 0.68, "ESP": 2.14, "AUT": 0.53, "POR": 1.5, "CRO": 0.88,
    "SUI": 1.62, "ALG": 0.99, "ARG": 2.57, "CPV": 0.48, "AUS": 0.95, "EGY": 1.13,
    "COL": 1.61, "GHA": 0.71,
}

# Clean sheet probability for the R32 match — build_r32.py (CS = e^(-opp_lambda),
# self-consistent with PROJ_GOALS). The 32 qualified teams.
CS_PCT = {
    "RSA": 0.19, "CAN": 0.45, "GER": 0.49, "PAR": 0.11, "BRA": 0.41, "JPN": 0.18,
    "NED": 0.37, "MAR": 0.25, "CIV": 0.21, "NOR": 0.33, "FRA": 0.48, "SWE": 0.09,
    "MEX": 0.42, "ECU": 0.3, "ENG": 0.56, "COD": 0.11, "BEL": 0.38, "SEN": 0.26,
    "USA": 0.51, "BIH": 0.12, "ESP": 0.59, "AUT": 0.12, "POR": 0.41, "CRO": 0.22,
    "SUI": 0.37, "ALG": 0.2, "ARG": 0.62, "CPV": 0.08, "AUS": 0.32, "EGY": 0.39,
    "COL": 0.49, "GHA": 0.2,
}

# FDR for the R32 match (1=easiest, 5=hardest) — build_r32.py
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR = {
    # 1 — easiest (facing very weak opponent)
    "GER": 1, "FRA": 1, "ENG": 1, "USA": 1, "ESP": 1, "ARG": 1,
    # 2 — easy
    "CAN": 2, "BRA": 2, "MEX": 2, "BEL": 2, "POR": 2, "SUI": 2, "COL": 2,
    # 3 — moderate
    "NED": 3, "NOR": 3, "ECU": 3, "AUS": 3, "EGY": 3,
    # 4 — hard
    "RSA": 4, "JPN": 4, "MAR": 4, "CIV": 4, "SEN": 4, "CRO": 4, "ALG": 4, "GHA": 4,
    # 5 — hardest (facing strong opponent)
    "PAR": 5, "SWE": 5, "COD": 5, "BIH": 5, "AUT": 5, "CPV": 5,
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

# Tournament qualification probabilities (0.0–1.0) per team — build_r32.py 50k
# Monte-Carlo of the locked R32 bracket. r32 = reaches last 32 (=1.0, already
# qualified), r16 = reaches last 16, qf = quarters, sf = semis, f = reaches final.
# R32 advance prob from the live bookmaker odds; R16+ from national-team Elo
# (data/elo_ratings.csv). Source of truth: data/r32_output.json.
QUAL_PROBS: dict[str, dict] = {
    "RSA": {"r32": 1.0, "r16": 0.2961, "qf": 0.07, "sf": 0.0112, "f": 0.0021},
    "CAN": {"r32": 1.0, "r16": 0.7039, "qf": 0.2035, "sf": 0.0411, "f": 0.0091},
    "GER": {"r32": 1.0, "r16": 0.8014, "qf": 0.3259, "sf": 0.2, "f": 0.0925},
    "PAR": {"r32": 1.0, "r16": 0.1986, "qf": 0.0354, "sf": 0.0112, "f": 0.0024},
    "BRA": {"r32": 1.0, "r16": 0.6883, "qf": 0.5377, "sf": 0.3423, "f": 0.1785},
    "JPN": {"r32": 1.0, "r16": 0.3117, "qf": 0.1725, "sf": 0.0676, "f": 0.0209},
    "NED": {"r32": 1.0, "r16": 0.5951, "qf": 0.4674, "sf": 0.2043, "f": 0.099},
    "MAR": {"r32": 1.0, "r16": 0.4049, "qf": 0.259, "sf": 0.0757, "f": 0.024},
    "CIV": {"r32": 1.0, "r16": 0.3967, "qf": 0.0998, "sf": 0.0309, "f": 0.0068},
    "NOR": {"r32": 1.0, "r16": 0.6033, "qf": 0.1901, "sf": 0.0713, "f": 0.0204},
    "FRA": {"r32": 1.0, "r16": 0.8261, "qf": 0.5842, "sf": 0.4364, "f": 0.2724},
    "SWE": {"r32": 1.0, "r16": 0.1739, "qf": 0.0545, "sf": 0.0202, "f": 0.0046},
    "MEX": {"r32": 1.0, "r16": 0.59, "qf": 0.1945, "sf": 0.0685, "f": 0.0198},
    "ECU": {"r32": 1.0, "r16": 0.41, "qf": 0.1283, "sf": 0.0431, "f": 0.0112},
    "ENG": {"r32": 1.0, "r16": 0.8299, "qf": 0.6159, "sf": 0.3614, "f": 0.1749},
    "COD": {"r32": 1.0, "r16": 0.1701, "qf": 0.0614, "sf": 0.0147, "f": 0.0027},
    "BEL": {"r32": 1.0, "r16": 0.6007, "qf": 0.3996, "sf": 0.1577, "f": 0.0695},
    "SEN": {"r32": 1.0, "r16": 0.3993, "qf": 0.2039, "sf": 0.0512, "f": 0.0152},
    "USA": {"r32": 1.0, "r16": 0.7985, "qf": 0.3393, "sf": 0.0921, "f": 0.0283},
    "BIH": {"r32": 1.0, "r16": 0.2015, "qf": 0.0572, "sf": 0.0098, "f": 0.0021},
    "ESP": {"r32": 1.0, "r16": 0.8352, "qf": 0.5528, "sf": 0.4204, "f": 0.2564},
    "AUT": {"r32": 1.0, "r16": 0.1648, "qf": 0.0495, "sf": 0.0217, "f": 0.0064},
    "POR": {"r32": 1.0, "r16": 0.6447, "qf": 0.2774, "sf": 0.1817, "f": 0.0902},
    "CRO": {"r32": 1.0, "r16": 0.3553, "qf": 0.1203, "sf": 0.0655, "f": 0.0259},
    "SUI": {"r32": 1.0, "r16": 0.6446, "qf": 0.3396, "sf": 0.1034, "f": 0.0389},
    "ALG": {"r32": 1.0, "r16": 0.3554, "qf": 0.1512, "sf": 0.0331, "f": 0.0093},
    "ARG": {"r32": 1.0, "r16": 0.8863, "qf": 0.786, "sf": 0.6354, "f": 0.4396},
    "CPV": {"r32": 1.0, "r16": 0.1137, "qf": 0.0488, "sf": 0.0146, "f": 0.0029},
    "AUS": {"r32": 1.0, "r16": 0.4548, "qf": 0.0693, "sf": 0.023, "f": 0.0049},
    "EGY": {"r32": 1.0, "r16": 0.5452, "qf": 0.0959, "sf": 0.0374, "f": 0.0099},
    "COL": {"r32": 1.0, "r16": 0.709, "qf": 0.4058, "sf": 0.1344, "f": 0.0551},
    "GHA": {"r32": 1.0, "r16": 0.291, "qf": 0.1034, "sf": 0.0187, "f": 0.0042},
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
