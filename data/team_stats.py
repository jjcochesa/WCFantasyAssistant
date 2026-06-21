"""
Hardcoded team-level data for WC 2026 — SINGLE upcoming match at a time.

From the group stage MD2 onward the model projects only the next round for each
team, then we wipe and refresh for the following round (MD2 → MD3 → R32 → R16 →
QF → SF → Final). Each round you send fresh CS% / xG and we swap the single
value per team below.

Sources:
  - Projected goals & CS% (MD3): Spreadex markets via @FPL_Fran (top-20 direct;
    opponent values Poisson-derived; SUI/CAN/KSA/CPV/ALG/AUT from FPLJoe)
  - FDR (1=easiest, 5=hardest): PELE ratings from FPLJoe image
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
    # Group A: MEX-CZE, KOR-RSA
    "MEX": "CZE", "CZE": "MEX", "KOR": "RSA", "RSA": "KOR",
    # Group B: SUI-CAN, QAT-BIH
    "SUI": "CAN", "CAN": "SUI", "QAT": "BIH", "BIH": "QAT",
    # Group C: BRA-SCO, MAR-HAI
    "BRA": "SCO", "SCO": "BRA", "MAR": "HAI", "HAI": "MAR",
    # Group D: USA-TUR, PAR-AUS
    "USA": "TUR", "TUR": "USA", "PAR": "AUS", "AUS": "PAR",
    # Group E: GER-ECU, CIV-CUW
    "GER": "ECU", "ECU": "GER", "CIV": "CUW", "CUW": "CIV",
    # Group F: NED-TUN, JPN-SWE
    "NED": "TUN", "TUN": "NED", "JPN": "SWE", "SWE": "JPN",
    # Group G: BEL-NZL, EGY-IRN
    "BEL": "NZL", "NZL": "BEL", "EGY": "IRN", "IRN": "EGY",
    # Group H: ESP-URU, KSA-CPV
    "ESP": "URU", "URU": "ESP", "KSA": "CPV", "CPV": "KSA",
    # Group I: FRA-NOR, SEN-IRQ
    "FRA": "NOR", "NOR": "FRA", "SEN": "IRQ", "IRQ": "SEN",
    # Group J: ARG-JOR, ALG-AUT
    "ARG": "JOR", "JOR": "ARG", "ALG": "AUT", "AUT": "ALG",
    # Group K: POR-COL, COD-UZB
    "POR": "COL", "COL": "POR", "COD": "UZB", "UZB": "COD",
    # Group L: ENG-PAN, CRO-GHA
    "ENG": "PAN", "PAN": "ENG", "CRO": "GHA", "GHA": "CRO",
}

# Projected goals for the upcoming match — Spreadex via @FPL_Fran (MD3)
# Top-20 teams read directly from image; opponent teams derived via Poisson
# (team CS% → opponent xG = -ln(CS%)). SUI/CAN/KSA/CPV/ALG/AUT kept from
# FPLJoe (absent from both Spreadex rankings).
PROJ_GOALS = {
    "NED": 2.85, "CIV": 2.82, "MAR": 2.66, "ARG": 2.60, "ENG": 2.55,
    "BEL": 2.48, "SEN": 2.23, "BIH": 2.20, "BRA": 2.06, "ESP": 1.95,
    "FRA": 1.83, "KOR": 1.78, "CRO": 1.73, "JPN": 1.72, "USA": 1.69,
    "GER": 1.69, "MEX": 1.54, "POR": 1.51, "COD": 1.45, "EGY": 1.35,
    "SUI": 1.32, "CAN": 1.17, "KSA": 1.30, "ALG": 1.17, "AUT": 1.27,
    "CPV": 1.17, "TUR": 1.27, "SWE": 1.11, "ECU": 1.08, "UZB": 1.08,
    "NOR": 1.02, "PAR": 1.02, "COL": 0.99, "AUS": 0.97, "CZE": 0.92,
    "IRN": 0.89, "QAT": 0.84, "URU": 0.82, "GHA": 0.82, "RSA": 0.78,
    "SCO": 0.69, "PAN": 0.62, "NZL": 0.58, "IRQ": 0.58, "JOR": 0.56,
    "HAI": 0.54, "TUN": 0.53, "CUW": 0.53,
}

# Clean sheet probability for the upcoming match — Spreadex via @FPL_Fran (MD3)
# Top-20 teams direct; opponent teams Poisson-derived (opp CS% = e^(-team xG)).
# JPN/USA/SUI/CAN/KSA/CPV/ALG/AUT kept from FPLJoe.
CS_PCT = {
    "NED": 0.59, "CIV": 0.59, "MAR": 0.58, "ARG": 0.57, "BEL": 0.56,
    "SEN": 0.56, "ENG": 0.54, "BRA": 0.50, "KOR": 0.46, "ESP": 0.44,
    "CRO": 0.44, "BIH": 0.43, "EGY": 0.41, "MEX": 0.40, "PAR": 0.38,
    "POR": 0.37, "FRA": 0.36, "AUS": 0.36, "GER": 0.34, "COD": 0.34,
    "JPN": 0.33, "SUI": 0.31, "KSA": 0.31, "AUT": 0.31, "USA": 0.28,
    "ALG": 0.28, "CAN": 0.27, "CPV": 0.27, "IRN": 0.26, "UZB": 0.24,
    "COL": 0.22, "CZE": 0.21, "ECU": 0.18, "TUR": 0.18, "SWE": 0.18,
    "GHA": 0.18, "NOR": 0.16, "RSA": 0.17, "URU": 0.14, "SCO": 0.13,
    "QAT": 0.11, "IRQ": 0.11, "PAN": 0.08, "NZL": 0.08, "JOR": 0.07,
    "HAI": 0.07, "TUN": 0.06, "CUW": 0.06,
}

# FDR for the upcoming match — FPLJoe.com (MD3, PELE ratings; 1=easiest, 5=hardest)
# Read directly from the fixture-cell colour bands (dark green→crimson).
FDR = {
    # 1 — dark green (easiest)
    "BIH": 1, "CIV": 1, "MAR": 1, "ARG": 1, "SEN": 1, "BEL": 1,
    "KSA": 1, "CPV": 1, "NED": 1, "KOR": 1, "QAT": 1, "CRO": 1,
    # 2 — bright green
    "COD": 2, "ENG": 2, "EGY": 2, "UZB": 2, "MEX": 2, "IRN": 2,
    # 3 — neutral grey
    "RSA": 3, "AUT": 3, "JPN": 3, "PAR": 3, "CUW": 3, "BRA": 3,
    "SUI": 3, "AUS": 3, "ALG": 3, "TUR": 3, "CZE": 3, "GHA": 3,
    "HAI": 3, "SWE": 3,
    # 4 — pink
    "USA": 4, "IRQ": 4, "CAN": 4, "NZL": 4, "GER": 4, "ESP": 4,
    "TUN": 4, "POR": 4, "FRA": 4, "COL": 4,
    # 5 — crimson (hardest)
    "SCO": 5, "ECU": 5, "NOR": 5, "PAN": 5, "URU": 5, "JOR": 5,
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
