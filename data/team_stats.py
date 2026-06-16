"""
Hardcoded team-level data for WC 2026 — SINGLE upcoming match at a time.

From the group stage MD2 onward the model projects only the next round for each
team, then we wipe and refresh for the following round (MD2 → MD3 → R32 → R16 →
QF → SF → Final). Each round you send fresh CS% / xG and we swap the single
value per team below.

Sources:
  - Projected goals & CS% from FPLJoe.com (SBOBET/Betfair markets)
  - FDR (1=easiest, 5=hardest) from @FPL_Marcello
  - Fixtures from official WC 2026 schedule
"""

# Label for the round currently being projected (display only)
CURRENT_ROUND = "MD2"
CURRENT_ROUND_DATE = "16.06.26"

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

# Next opponent (3-letter code) for the upcoming round
FIXTURES = {
    "SUI": "BIH", "CAN": "QAT", "QAT": "CAN", "BIH": "SUI",
    "GER": "CIV", "ECU": "CUW", "CIV": "GER", "CUW": "ECU",
    "BEL": "IRN", "IRN": "BEL", "EGY": "NZL", "NZL": "EGY",
    "ESP": "KSA", "URU": "CPV", "KSA": "ESP", "CPV": "URU",
    "MEX": "KOR", "KOR": "MEX", "CZE": "RSA", "RSA": "CZE",
    "BRA": "HAI", "MAR": "SCO", "SCO": "MAR", "HAI": "BRA",
    "ARG": "AUT", "AUT": "ARG", "ALG": "JOR", "JOR": "ALG",
    "POR": "UZB", "COL": "COD", "COD": "COL", "UZB": "POR",
    "NED": "SWE", "JPN": "TUN", "SWE": "NED", "TUN": "JPN",
    "USA": "AUS", "TUR": "PAR", "AUS": "USA", "PAR": "TUR",
    "FRA": "IRQ", "SEN": "NOR", "NOR": "SEN", "IRQ": "FRA",
    "ENG": "GHA", "CRO": "PAN", "GHA": "ENG", "PAN": "CRO",
}

# Projected goals for the upcoming match — FPLJoe.com (16.06.26 / MD2)
PROJ_GOALS = {
    "ESP": 2.98, "GER": 1.80, "BRA": 3.53, "FRA": 2.79, "POR": 2.43, "ENG": 2.30,
    "ARG": 1.55, "BEL": 1.88, "SUI": 1.71, "NED": 1.83, "MEX": 1.50, "NOR": 1.51,
    "URU": 1.90, "COL": 1.74, "AUT": 0.74, "USA": 1.70, "CAN": 1.99, "ECU": 2.42,
    "MAR": 1.38, "CRO": 1.68, "TUR": 1.27, "CIV": 0.82, "JPN": 1.64, "EGY": 1.44,
    "SEN": 1.06, "SCO": 0.82, "CZE": 1.43, "KOR": 0.86, "SWE": 1.01, "ALG": 1.63,
    "PAR": 0.88, "IRN": 0.69, "BIH": 0.83, "GHA": 0.74, "AUS": 0.93, "RSA": 0.88,
    "TUN": 0.70, "COD": 0.63, "UZB": 0.61, "PAN": 0.67, "KSA": 0.42, "NZL": 0.76,
    "CPV": 0.60, "QAT": 0.61, "JOR": 0.79, "HAI": 0.45, "IRQ": 0.42, "CUW": 0.44,
}

# Clean sheet probability for the upcoming match — FPLJoe.com (16.06.26 / MD2)
CS_PCT = {
    "ESP": 0.66, "ARG": 0.48, "FRA": 0.66, "BRA": 0.64, "GER": 0.44, "ENG": 0.48,
    "POR": 0.54, "BEL": 0.50, "SUI": 0.44, "MEX": 0.43, "COL": 0.53, "NED": 0.37,
    "CAN": 0.54, "ECU": 0.64, "URU": 0.55, "CRO": 0.51, "USA": 0.40, "MAR": 0.44,
    "NOR": 0.33, "TUR": 0.41, "AUT": 0.21, "CIV": 0.18, "EGY": 0.47, "JPN": 0.50,
    "CZE": 0.42, "KOR": 0.22, "SCO": 0.25, "IRN": 0.15, "SEN": 0.22, "SWE": 0.16,
    "ALG": 0.45, "BIH": 0.18, "GHA": 0.10, "RSA": 0.24, "AUS": 0.18, "TUN": 0.19,
    "PAR": 0.28, "COD": 0.18, "KSA": 0.04, "UZB": 0.09, "NZL": 0.24, "CPV": 0.18,
    "QAT": 0.14, "PAN": 0.19, "JOR": 0.20, "HAI": 0.03, "IRQ": 0.06, "CUW": 0.09,
}

# FDR for the upcoming match — @FPL_Marcello (1=easiest, 5=hardest)
FDR = {
    "BEL": 1, "MEX": 2, "EGY": 1, "ESP": 2, "ARG": 3, "POR": 1, "CZE": 1, "SUI": 3,
    "BRA": 1, "GER": 2, "IRN": 4, "NZL": 2, "URU": 1, "COL": 1, "ENG": 2, "CAN": 1,
    "BIH": 4, "MAR": 2, "USA": 1, "TUR": 3, "ECU": 1, "NED": 3, "JOR": 2, "AUT": 5,
    "SCO": 2, "KOR": 4, "RSA": 2, "FRA": 1, "NOR": 2, "ALG": 1, "SEN": 2, "PAR": 4,
    "JPN": 3, "QAT": 3, "SWE": 4, "CIV": 5, "TUN": 4, "HAI": 5, "AUS": 4, "GHA": 4,
    "PAN": 3, "CRO": 1, "COD": 1, "UZB": 5, "CPV": 1, "KSA": 5, "IRQ": 5, "CUW": 2,
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
