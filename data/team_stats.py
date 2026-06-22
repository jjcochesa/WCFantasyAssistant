"""
Hardcoded team-level data for WC 2026 — SINGLE upcoming match at a time.

From the group stage MD2 onward the model projects only the next round for each
team, then we wipe and refresh for the following round (MD2 → MD3 → R32 → R16 →
QF → SF → Final). Each round you send fresh CS% / xG and we swap the single
value per team below.

Sources:
  - Projected goals & CS% (MD3): FPLJoe.com via SBOBET & Betfair Exchange markets
    (all 48 teams direct — no Poisson derivation)
  - FDR (1=easiest, 5=hardest): derived from opponent threat = avg(opp_xGF, opp_CS%)
    banded into 5 tiers, consistent with FPLJoe PELE colour bands
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

# Projected goals for the upcoming match — FPLJoe.com MD3 (SBOBET & Betfair)
# All 48 teams direct.
PROJ_GOALS = {
    "NED": 2.91, "CIV": 2.78, "MAR": 2.62, "BEL": 2.52, "ARG": 2.50,
    "ENG": 2.49, "BIH": 2.17, "SEN": 2.16, "BRA": 2.07, "ESP": 1.96,
    "FRA": 1.76, "CRO": 1.74, "KOR": 1.73, "USA": 1.71, "JPN": 1.70,
    "GER": 1.65, "MEX": 1.54, "COD": 1.46, "POR": 1.46, "CPV": 1.35,
    "AUT": 1.30, "SUI": 1.30, "ALG": 1.21, "KSA": 1.19, "EGY": 1.16,
    "TUR": 1.16, "CAN": 1.14, "SWE": 1.14, "ECU": 1.13, "NOR": 1.05,
    "UZB": 1.03, "COL": 1.03, "PAR": 1.00, "CZE": 0.98, "AUS": 0.97,
    "IRN": 0.96, "QAT": 0.86, "RSA": 0.80, "URU": 0.79, "GHA": 0.77,
    "SCO": 0.67, "PAN": 0.59, "NZL": 0.56, "IRQ": 0.55, "HAI": 0.53,
    "CUW": 0.52, "JOR": 0.52, "TUN": 0.46,
}

# Clean sheet probability for the upcoming match — FPLJoe.com MD3 (SBOBET & Betfair)
# All 48 teams direct.
CS_PCT = {
    "NED": 0.63, "ARG": 0.60, "CIV": 0.60, "MAR": 0.59, "SEN": 0.58,
    "BEL": 0.57, "ENG": 0.55, "BRA": 0.51, "CRO": 0.47, "ESP": 0.46,
    "KOR": 0.45, "BIH": 0.42, "EGY": 0.38, "PAR": 0.38, "MEX": 0.38,
    "AUS": 0.37, "POR": 0.36, "COD": 0.36, "FRA": 0.35, "GER": 0.32,
    "JPN": 0.32, "SUI": 0.32, "USA": 0.31, "IRN": 0.31, "CPV": 0.30,
    "AUT": 0.30, "ALG": 0.27, "CAN": 0.27, "KSA": 0.26, "COL": 0.23,
    "UZB": 0.23, "CZE": 0.21, "ECU": 0.19, "SWE": 0.18, "TUR": 0.18,
    "RSA": 0.18, "GHA": 0.18, "NOR": 0.17, "URU": 0.14, "SCO": 0.13,
    "IRQ": 0.11, "QAT": 0.11, "PAN": 0.08, "JOR": 0.08, "NZL": 0.08,
    "HAI": 0.07, "CUW": 0.06, "TUN": 0.05,
}

# FDR for the upcoming match — FPLJoe.com MD3 (1=easiest, 5=hardest)
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR = {
    # 1 — easiest (facing very weak opponent)
    "BRA": 1, "MAR": 1, "BEL": 1, "ARG": 1, "NED": 1, "CIV": 1, "SEN": 1, "ENG": 1,
    # 2 — easy
    "CRO": 2, "BIH": 2, "KOR": 2, "ESP": 2, "FRA": 2, "MEX": 2,
    # 3 — moderate
    "COD": 3, "EGY": 3, "CPV": 3, "KSA": 3, "AUT": 3, "ALG": 3,
    "SUI": 3, "CAN": 3, "PAR": 3, "AUS": 3, "IRN": 3, "JPN": 3,
    "GER": 3, "USA": 3, "POR": 3,
    # 4 — hard
    "UZB": 4, "COL": 4, "SWE": 4, "TUR": 4, "CZE": 4, "ECU": 4,
    "NOR": 4, "RSA": 4, "GHA": 4,
    # 5 — hardest (facing strong opponent)
    "IRQ": 5, "SCO": 5, "QAT": 5, "URU": 5, "JOR": 5, "HAI": 5,
    "NZL": 5, "TUN": 5, "PAN": 5, "CUW": 5,
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
