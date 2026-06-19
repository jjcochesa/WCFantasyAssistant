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
CURRENT_ROUND = "MD3"
CURRENT_ROUND_DATE = "22.06.26"

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
    # Group A: MEX-RSA, KOR-CZE
    "MEX": "RSA", "RSA": "MEX", "KOR": "CZE", "CZE": "KOR",
    # Group B: SUI-CAN, QAT-BIH
    "SUI": "CAN", "CAN": "SUI", "QAT": "BIH", "BIH": "QAT",
    # Group C: BRA-SCO, MAR-HAI
    "BRA": "SCO", "SCO": "BRA", "MAR": "HAI", "HAI": "MAR",
    # Group D: USA-PAR, TUR-AUS
    "USA": "PAR", "PAR": "USA", "TUR": "AUS", "AUS": "TUR",
    # Group E: ECU-CIV, GER-CUW
    "ECU": "CIV", "CIV": "ECU", "GER": "CUW", "CUW": "GER",
    # Group F: NED-TUN, JPN-SWE
    "NED": "TUN", "TUN": "NED", "JPN": "SWE", "SWE": "JPN",
    # Group G: BEL-NZL, EGY-IRN
    "BEL": "NZL", "NZL": "BEL", "EGY": "IRN", "IRN": "EGY",
    # Group H: ESP-CPV, URU-KSA
    "ESP": "CPV", "CPV": "ESP", "URU": "KSA", "KSA": "URU",
    # Group I: FRA-NOR, SEN-IRQ
    "FRA": "NOR", "NOR": "FRA", "SEN": "IRQ", "IRQ": "SEN",
    # Group J: ARG-JOR, ALG-AUT
    "ARG": "JOR", "JOR": "ARG", "ALG": "AUT", "AUT": "ALG",
    # Group K: POR-COD, COL-UZB
    "POR": "COD", "COD": "POR", "COL": "UZB", "UZB": "COL",
    # Group L: ENG-PAN, CRO-GHA
    "ENG": "PAN", "PAN": "ENG", "CRO": "GHA", "GHA": "CRO",
}

# Projected goals for the upcoming match — FPLJoe.com (MD3 / SBOBET & Betfair)
PROJ_GOALS = {
    "CIV": 2.88, "BEL": 2.49, "ARG": 2.47, "ENG": 2.42, "MAR": 2.34, "SEN": 2.13,
    "NED": 2.12, "BRA": 2.01, "ESP": 1.92, "BIH": 1.78, "GER": 1.76, "CRO": 1.71,
    "FRA": 1.72, "MEX": 1.57, "KOR": 1.54, "USA": 1.49, "POR": 1.47, "JPN": 1.46,
    "SUI": 1.41, "PAR": 1.34, "KSA": 1.30, "AUT": 1.28, "COD": 1.27, "TUR": 1.27,
    "CPV": 1.17, "ALG": 1.16, "SWE": 1.11, "CAN": 1.07, "UZB": 1.05, "RSA": 1.01,
    "AUS": 0.98, "EGY": 1.32, "NOR": 1.18, "COL": 1.04, "CZE": 0.89, "TUN": 0.89,
    "ECU": 0.89, "URU": 0.85, "IRN": 0.85, "GHA": 0.79, "QAT": 0.78, "SCO": 0.76,
    "NZL": 0.72, "HAI": 0.69, "JOR": 0.63, "IRQ": 0.58, "CUW": 0.50, "PAN": 0.65,
}

# Clean sheet probability for the upcoming match — FPLJoe.com (MD3 / SBOBET & Betfair)
CS_PCT = {
    "CIV": 0.61, "BEL": 0.57, "ENG": 0.52, "ARG": 0.54, "SEN": 0.56, "COL": 0.56,
    "MAR": 0.50, "BRA": 0.47, "AUT": 0.46, "BIH": 0.46, "CRO": 0.45, "ESP": 0.43,
    "EGY": 0.43, "NED": 0.41, "MEX": 0.41, "AUS": 0.41, "GER": 0.41, "SUI": 0.34,
    "POR": 0.35, "COD": 0.35, "JPN": 0.33, "FRA": 0.33, "PAR": 0.38, "KOR": 0.36,
    "TUN": 0.31, "KSA": 0.31, "CAN": 0.24, "SWE": 0.23, "TUR": 0.22, "RSA": 0.21,
    "CZE": 0.21, "GHA": 0.18, "NOR": 0.18, "IRQ": 0.12, "URU": 0.15, "ALG": 0.28,
    "USA": 0.28, "UZB": 0.28, "CPV": 0.27, "IRN": 0.27, "QAT": 0.17, "ECU": 0.17,
    "SCO": 0.13, "HAI": 0.10, "PAN": 0.09, "JOR": 0.08, "NZL": 0.08, "CUW": 0.06,
}

# FDR for the upcoming match — estimated for MD3 (1=easiest, 5=hardest)
FDR = {
    # Group A: MEX-RSA, KOR-CZE
    "MEX": 2, "RSA": 5, "KOR": 3, "CZE": 3,
    # Group B: SUI-CAN, QAT-BIH
    "SUI": 3, "CAN": 4, "QAT": 3, "BIH": 3,
    # Group C: BRA-SCO, MAR-HAI
    "BRA": 1, "SCO": 5, "MAR": 2, "HAI": 5,
    # Group D: USA-PAR, TUR-AUS
    "USA": 3, "PAR": 3, "TUR": 3, "AUS": 3,
    # Group E: ECU-CIV, GER-CUW
    "ECU": 4, "CIV": 3, "GER": 1, "CUW": 5,
    # Group F: NED-TUN, JPN-SWE
    "NED": 2, "TUN": 4, "JPN": 3, "SWE": 3,
    # Group G: BEL-NZL, EGY-IRN
    "BEL": 1, "NZL": 5, "EGY": 3, "IRN": 3,
    # Group H: ESP-CPV, URU-KSA
    "ESP": 1, "CPV": 5, "URU": 2, "KSA": 4,
    # Group I: FRA-NOR, SEN-IRQ
    "FRA": 2, "NOR": 5, "SEN": 2, "IRQ": 4,
    # Group J: ARG-JOR, ALG-AUT
    "ARG": 1, "JOR": 5, "ALG": 3, "AUT": 3,
    # Group K: POR-COD, COL-UZB
    "POR": 1, "COD": 5, "COL": 2, "UZB": 4,
    # Group L: ENG-PAN, CRO-GHA
    "ENG": 1, "PAN": 5, "CRO": 2, "GHA": 4,
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
