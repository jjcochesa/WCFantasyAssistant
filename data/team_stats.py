"""
Hardcoded team-level data for WC 2026 group stage.
Sources:
  - Projected goals & CS% from FPLJoe.com (from SBOBET/Betfair markets)
  - FDR (1=easiest, 5=hardest) from @FPL_Marcello
  - Fixtures from official WC 2026 schedule

Updated 16.06.26: shifted to MD2+MD3 (MD1 played). Index 0 = MD2, 1 = MD3, 2 = placeholder.
"""

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

# Fixtures: [MD2_opponent, MD3_opponent, ""] — MD1 complete
FIXTURES = {
    "SUI": ["BIH", "CAN", ""],  "CAN": ["QAT", "SUI", ""],
    "QAT": ["CAN", "BIH", ""],  "BIH": ["SUI", "QAT", ""],
    "GER": ["CIV", "ECU", ""],  "ECU": ["CUW", "GER", ""],
    "CIV": ["GER", "CUW", ""],  "CUW": ["ECU", "CIV", ""],
    "BEL": ["IRN", "NZL", ""],  "IRN": ["BEL", "EGY", ""],
    "EGY": ["NZL", "IRN", ""],  "NZL": ["EGY", "BEL", ""],
    "ESP": ["KSA", "URU", ""],  "URU": ["CPV", "ESP", ""],
    "KSA": ["ESP", "CPV", ""],  "CPV": ["URU", "KSA", ""],
    "MEX": ["KOR", "CZE", ""],  "KOR": ["MEX", "RSA", ""],
    "CZE": ["RSA", "MEX", ""],  "RSA": ["CZE", "KOR", ""],
    "BRA": ["HAI", "SCO", ""],  "MAR": ["SCO", "HAI", ""],
    "SCO": ["MAR", "BRA", ""],  "HAI": ["BRA", "MAR", ""],
    "ARG": ["AUT", "JOR", ""],  "AUT": ["ARG", "ALG", ""],
    "ALG": ["JOR", "AUT", ""],  "JOR": ["ALG", "ARG", ""],
    "POR": ["UZB", "COL", ""],  "COL": ["COD", "POR", ""],
    "COD": ["COL", "UZB", ""],  "UZB": ["POR", "COD", ""],
    "NED": ["SWE", "TUN", ""],  "JPN": ["TUN", "SWE", ""],
    "SWE": ["NED", "JPN", ""],  "TUN": ["JPN", "NED", ""],
    "USA": ["AUS", "TUR", ""],  "TUR": ["PAR", "USA", ""],
    "AUS": ["USA", "PAR", ""],  "PAR": ["TUR", "AUS", ""],
    "FRA": ["IRQ", "NOR", ""],  "SEN": ["NOR", "IRQ", ""],
    "NOR": ["SEN", "FRA", ""],  "IRQ": ["FRA", "SEN", ""],
    "ENG": ["GHA", "PAN", ""],  "CRO": ["PAN", "GHA", ""],
    "GHA": ["ENG", "CRO", ""],  "PAN": ["CRO", "ENG", ""],
}

# Projected goals scored per matchday [MD2, MD3, placeholder] — FPLJoe.com (16.06.26)
PROJ_GOALS = {
    "ESP": [2.98, 1.78, 0.0], "GER": [1.80, 1.77, 0.0], "BRA": [3.53, 2.00, 0.0],
    "FRA": [2.79, 1.64, 0.0], "POR": [2.43, 1.47, 0.0], "ENG": [2.30, 2.26, 0.0],
    "ARG": [1.55, 2.47, 0.0], "BEL": [1.88, 2.22, 0.0], "SUI": [1.71, 1.41, 0.0],
    "NED": [1.83, 1.90, 0.0], "MEX": [1.50, 1.54, 0.0], "NOR": [1.51, 1.00, 0.0],
    "URU": [1.90, 0.90, 0.0], "COL": [1.74, 1.04, 0.0], "AUT": [0.74, 1.35, 0.0],
    "USA": [1.70, 1.37, 0.0], "CAN": [1.99, 1.04, 0.0], "ECU": [2.42, 0.95, 0.0],
    "MAR": [1.38, 2.11, 0.0], "CRO": [1.68, 1.64, 0.0], "TUR": [1.27, 1.28, 0.0],
    "CIV": [0.82, 2.41, 0.0], "JPN": [1.64, 1.45, 0.0], "EGY": [1.44, 1.22, 0.0],
    "SEN": [1.06, 1.89, 0.0], "SCO": [0.82, 0.79, 0.0], "CZE": [1.43, 0.92, 0.0],
    "KOR": [0.86, 1.47, 0.0], "SWE": [1.01, 1.05, 0.0], "ALG": [1.63, 1.10, 0.0],
    "PAR": [0.88, 1.31, 0.0], "IRN": [0.69, 0.91, 0.0], "BIH": [0.83, 1.79, 0.0],
    "GHA": [0.74, 0.79, 0.0], "AUS": [0.93, 1.00, 0.0], "RSA": [0.88, 0.94, 0.0],
    "TUN": [0.70, 0.76, 0.0], "COD": [0.63, 1.23, 0.0], "UZB": [0.61, 1.02, 0.0],
    "PAN": [0.67, 0.70, 0.0], "KSA": [0.42, 1.14, 0.0], "NZL": [0.76, 0.65, 0.0],
    "CPV": [0.60, 1.22, 0.0], "QAT": [0.61, 0.76, 0.0], "JOR": [0.79, 0.61, 0.0],
    "HAI": [0.45, 0.64, 0.0], "IRQ": [0.42, 0.77, 0.0], "CUW": [0.44, 0.57, 0.0],
}

# Clean sheet probability per matchday [MD2, MD3, placeholder] — FPLJoe.com (16.06.26)
CS_PCT = {
    "ESP": [0.66, 0.41, 0.0], "ARG": [0.48, 0.46, 0.0], "FRA": [0.66, 0.37, 0.0],
    "BRA": [0.64, 0.46, 0.0], "GER": [0.44, 0.39, 0.0], "ENG": [0.48, 0.50, 0.0],
    "POR": [0.54, 0.35, 0.0], "BEL": [0.50, 0.52, 0.0], "SUI": [0.44, 0.35, 0.0],
    "MEX": [0.43, 0.40, 0.0], "COL": [0.53, 0.23, 0.0], "NED": [0.37, 0.47, 0.0],
    "CAN": [0.54, 0.24, 0.0], "ECU": [0.64, 0.17, 0.0], "URU": [0.55, 0.17, 0.0],
    "CRO": [0.51, 0.45, 0.0], "USA": [0.40, 0.28, 0.0], "MAR": [0.44, 0.53, 0.0],
    "NOR": [0.33, 0.19, 0.0], "TUR": [0.41, 0.25, 0.0], "AUT": [0.21, 0.33, 0.0],
    "CIV": [0.18, 0.57, 0.0], "EGY": [0.47, 0.40, 0.0], "JPN": [0.50, 0.35, 0.0],
    "CZE": [0.42, 0.21, 0.0], "KOR": [0.22, 0.39, 0.0], "SCO": [0.25, 0.14, 0.0],
    "IRN": [0.15, 0.30, 0.0], "SEN": [0.22, 0.46, 0.0], "SWE": [0.16, 0.23, 0.0],
    "ALG": [0.45, 0.26, 0.0], "BIH": [0.18, 0.47, 0.0], "GHA": [0.10, 0.19, 0.0],
    "RSA": [0.24, 0.23, 0.0], "AUS": [0.18, 0.27, 0.0], "TUN": [0.19, 0.15, 0.0],
    "PAR": [0.28, 0.37, 0.0], "COD": [0.18, 0.36, 0.0], "KSA": [0.04, 0.30, 0.0],
    "UZB": [0.09, 0.29, 0.0], "NZL": [0.24, 0.11, 0.0], "CPV": [0.18, 0.32, 0.0],
    "QAT": [0.14, 0.17, 0.0], "PAN": [0.19, 0.10, 0.0], "JOR": [0.20, 0.08, 0.0],
    "HAI": [0.03, 0.12, 0.0], "IRQ": [0.06, 0.15, 0.0], "CUW": [0.09, 0.09, 0.0],
}

# FDR per matchday [MD2, MD3, placeholder] — @FPL_Marcello (1=easiest, 5=hardest)
FDR = {
    "BEL": [1, 1, 3], "MEX": [2, 3, 3], "EGY": [1, 1, 3], "ESP": [2, 3, 3],
    "ARG": [3, 1, 3], "POR": [1, 4, 3], "CZE": [1, 4, 3], "SUI": [3, 3, 3],
    "BRA": [1, 2, 3], "GER": [2, 4, 3], "IRN": [4, 2, 3], "NZL": [2, 4, 3],
    "URU": [1, 5, 3], "COL": [1, 5, 3], "ENG": [2, 1, 3], "CAN": [1, 4, 3],
    "BIH": [4, 1, 3], "MAR": [2, 1, 3], "USA": [1, 4, 3], "TUR": [3, 4, 3],
    "ECU": [1, 5, 3], "NED": [3, 1, 3], "JOR": [2, 5, 3], "AUT": [5, 2, 3],
    "SCO": [2, 5, 3], "KOR": [4, 1, 3], "RSA": [2, 1, 3], "FRA": [1, 5, 3],
    "NOR": [2, 5, 3], "ALG": [1, 2, 3], "SEN": [2, 1, 3], "PAR": [4, 1, 3],
    "JPN": [3, 1, 3], "QAT": [3, 4, 3], "SWE": [4, 3, 3], "CIV": [5, 1, 3],
    "TUN": [4, 3, 3], "HAI": [5, 2, 3], "AUS": [4, 3, 3], "GHA": [4, 3, 3],
    "PAN": [3, 4, 3], "CRO": [1, 2, 3], "COD": [1, 1, 3], "UZB": [5, 1, 3],
    "CPV": [1, 2, 3], "KSA": [5, 2, 3], "IRQ": [5, 3, 3], "CUW": [2, 1, 3],
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

# Combined projection lookup: {team: {md1: (xg, cs_pct), md2: ..., md3: ...}}
TEAM_PROJECTIONS = {
    code: {
        "md1": (PROJ_GOALS[code][0], CS_PCT.get(code, [0.3, 0.3, 0.3])[0]),
        "md2": (PROJ_GOALS[code][1], CS_PCT.get(code, [0.3, 0.3, 0.3])[1]),
        "md3": (PROJ_GOALS[code][2], CS_PCT.get(code, [0.3, 0.3, 0.3])[2]),
    }
    for code in PROJ_GOALS
}


def get_team_proj(team_code: str, md: int) -> tuple:
    """Returns (team_xg, cs_pct) for matchday 1/2/3."""
    return TEAM_PROJECTIONS.get(team_code, {}).get(f"md{md}", (1.0, 0.3))


def get_opponent_xg(team_code: str, md: int) -> float:
    """Estimate opponent xG from cs_pct via Poisson: P(CS) = e^(-λ) → λ = -ln(cs_pct)."""
    _, cs_pct = get_team_proj(team_code, md)
    return -_math.log(max(cs_pct, 0.01))


def get_team_fdr_total(team_code: str) -> int:
    """Total FDR for remaining group stage games (MD2+MD3). Lower = easier fixtures."""
    fdr = FDR.get(team_code, [3, 3])
    return sum(fdr[:2])

def get_avg_cs_pct(team_code: str) -> float:
    """Average clean sheet probability across remaining 2 group stage games."""
    cs = CS_PCT.get(team_code, [0.3, 0.3])
    return sum(cs[:2]) / 2

def get_avg_proj_goals(team_code: str) -> float:
    """Average projected goals per game across remaining 2 group stage games."""
    g = PROJ_GOALS.get(team_code, [1.0, 1.0])
    return sum(g[:2]) / 2

def get_team_group(team_code: str) -> str:
    for grp, teams in GROUPS.items():
        if team_code in teams:
            return grp
    return "?"

def get_group_balance(team_code: str) -> str:
    grp = get_team_group(team_code)
    return GROUP_BALANCE.get(grp, "Unknown")
