"""
Hardcoded team-level data for WC 2026 group stage.
Sources:
  - Projected goals & CS% from FPLJoe.com (from SBOBET/Betfair markets)
  - FDR (1=easiest, 5=hardest) from @FPL_Marcello
  - Fixtures from official WC 2026 schedule
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

# Fixtures: [MD1_opponent, MD2_opponent, MD3_opponent]
FIXTURES = {
    "SUI": ["QAT", "BIH", "CAN"], "CAN": ["BIH", "QAT", "SUI"],
    "QAT": ["SUI", "CAN", "BIH"], "BIH": ["CAN", "SUI", "QAT"],
    "GER": ["CUW", "CIV", "ECU"], "ECU": ["CIV", "CUW", "GER"],
    "CIV": ["ECU", "GER", "CUW"], "CUW": ["GER", "ECU", "CIV"],
    "BEL": ["EGY", "IRN", "NZL"], "IRN": ["NZL", "BEL", "EGY"],
    "EGY": ["BEL", "NZL", "IRN"], "NZL": ["IRN", "EGY", "BEL"],
    "ESP": ["CPV", "KSA", "URU"], "URU": ["KSA", "CPV", "ESP"],
    "KSA": ["URU", "ESP", "CPV"], "CPV": ["ESP", "URU", "KSA"],
    "MEX": ["RSA", "KOR", "CZE"], "KOR": ["CZE", "MEX", "RSA"],
    "CZE": ["KOR", "RSA", "MEX"], "RSA": ["MEX", "CZE", "KOR"],
    "BRA": ["MAR", "HAI", "SCO"], "MAR": ["BRA", "SCO", "HAI"],
    "SCO": ["HAI", "MAR", "BRA"], "HAI": ["SCO", "BRA", "MAR"],
    "ARG": ["ALG", "AUT", "JOR"], "AUT": ["JOR", "ARG", "ALG"],
    "ALG": ["ARG", "JOR", "AUT"], "JOR": ["AUT", "ALG", "ARG"],
    "POR": ["COD", "UZB", "COL"], "COL": ["UZB", "COD", "POR"],
    "COD": ["POR", "COL", "UZB"], "UZB": ["COL", "POR", "COD"],
    "NED": ["JPN", "SWE", "TUN"], "JPN": ["NED", "TUN", "SWE"],
    "SWE": ["TUN", "NED", "JPN"], "TUN": ["SWE", "NED", "JPN"],
    "USA": ["PAR", "AUS", "TUR"], "TUR": ["AUS", "PAR", "USA"],
    "AUS": ["TUR", "USA", "PAR"], "PAR": ["USA", "TUR", "AUS"],
    "FRA": ["SEN", "IRQ", "NOR"], "SEN": ["FRA", "NOR", "IRQ"],
    "NOR": ["IRQ", "SEN", "FRA"], "IRQ": ["NOR", "FRA", "SEN"],
    "ENG": ["CRO", "GHA", "PAN"], "CRO": ["ENG", "PAN", "GHA"],
    "GHA": ["PAN", "ENG", "CRO"], "PAN": ["GHA", "CRO", "ENG"],
}

# Projected goals scored per matchday [MD1, MD2, MD3] — FPLJoe.com
PROJ_GOALS = {
    "ESP": [3.17, 2.93, 1.78], "GER": [4.04, 2.00, 1.77], "BRA": [1.71, 3.46, 2.00],
    "FRA": [1.93, 2.85, 1.64], "POR": [2.34, 2.47, 1.47], "ENG": [1.61, 2.24, 2.26],
    "ARG": [1.99, 1.75, 2.47], "BEL": [1.73, 2.02, 2.22], "SUI": [2.43, 1.76, 1.41],
    "NED": [1.55, 1.82, 1.90], "MEX": [1.83, 1.53, 1.54], "NOR": [2.53, 1.51, 1.00],
    "URU": [1.92, 1.98, 0.90], "COL": [1.94, 1.82, 1.04], "AUT": [2.30, 0.84, 1.35],
    "USA": [1.39, 1.63, 1.37], "CAN": [1.53, 2.10, 1.04], "ECU": [1.09, 2.47, 0.95],
    "MAR": [0.83, 1.44, 2.11], "CRO": [0.84, 1.86, 1.64], "TUR": [1.63, 1.29, 1.28],
    "CIV": [0.92, 0.88, 2.41], "JPN": [1.11, 1.55, 1.45], "EGY": [0.85, 1.56, 1.22],
    "SEN": [0.76, 1.10, 1.89], "SCO": [1.90, 0.89, 0.79], "CZE": [1.11, 1.42, 0.92],
    "KOR": [1.20, 0.87, 1.47], "SWE": [1.44, 0.89, 1.05], "ALG": [0.64, 1.83, 1.10],
    "PAR": [0.90, 1.01, 1.31], "IRN": [1.43, 0.69, 0.91], "BIH": [0.85, 0.80, 1.79],
    "GHA": [1.39, 0.67, 0.79], "AUS": [0.91, 0.92, 1.00], "RSA": [0.61, 0.90, 0.94],
    "TUN": [0.88, 0.83, 0.76], "COD": [0.61, 0.58, 1.23], "UZB": [0.66, 0.69, 1.02],
    "PAN": [0.97, 0.70, 0.70], "KSA": [0.71, 0.40, 1.14], "NZL": [0.88, 0.86, 0.65],
    "CPV": [0.49, 0.68, 1.22], "QAT": [0.55, 0.51, 0.76], "JOR": [0.72, 0.75, 0.61],
    "HAI": [0.77, 0.51, 0.64], "IRQ": [0.56, 0.39, 0.77], "CUW": [0.40, 0.49, 0.57],
}

# Clean sheet probability per matchday [MD1, MD2, MD3] — FPLJoe.com (from betting markets)
CS_PCT = {
    "ESP": [0.62, 0.67, 0.41], "ARG": [0.53, 0.60, 0.46], "FRA": [0.47, 0.68, 0.37],
    "BRA": [0.44, 0.60, 0.46], "GER": [0.67, 0.42, 0.39], "ENG": [0.43, 0.51, 0.50],
    "POR": [0.54, 0.50, 0.35], "BEL": [0.43, 0.50, 0.52], "SUI": [0.58, 0.45, 0.35],
    "MEX": [0.55, 0.42, 0.40], "COL": [0.52, 0.56, 0.23], "NED": [0.33, 0.41, 0.47],
    "CAN": [0.43, 0.60, 0.24], "ECU": [0.40, 0.61, 0.17], "URU": [0.49, 0.51, 0.17],
    "CRO": [0.20, 0.50, 0.45], "USA": [0.41, 0.40, 0.28], "MAR": [0.18, 0.41, 0.53],
    "NOR": [0.57, 0.33, 0.19], "TUR": [0.40, 0.36, 0.25], "AUT": [0.49, 0.17, 0.33],
    "CIV": [0.33, 0.14, 0.57], "EGY": [0.18, 0.43, 0.40], "JPN": [0.21, 0.44, 0.35],
    "CZE": [0.30, 0.41, 0.21], "KOR": [0.33, 0.22, 0.39], "SCO": [0.46, 0.24, 0.14],
    "IRN": [0.41, 0.13, 0.30], "SEN": [0.15, 0.22, 0.46], "SWE": [0.41, 0.16, 0.23],
    "ALG": [0.14, 0.47, 0.26], "BIH": [0.22, 0.17, 0.47], "GHA": [0.38, 0.11, 0.19],
    "RSA": [0.16, 0.24, 0.23], "AUS": [0.19, 0.20, 0.27], "TUN": [0.24, 0.21, 0.15],
    "PAR": [0.25, 0.27, 0.37], "COD": [0.10, 0.16, 0.36], "KSA": [0.15, 0.05, 0.30],
    "UZB": [0.14, 0.08, 0.29], "NZL": [0.24, 0.21, 0.11], "CPV": [0.04, 0.14, 0.32],
    "QAT": [0.09, 0.12, 0.17], "PAN": [0.25, 0.16, 0.10], "JOR": [0.10, 0.16, 0.08],
    "HAI": [0.15, 0.03, 0.12], "IRQ": [0.08, 0.06, 0.15], "CUW": [0.02, 0.08, 0.09],
}

# FDR per matchday [MD1, MD2, MD3] — @FPL_Marcello (1=easiest, 5=hardest)
FDR = {
    "BEL": [2, 1, 1], "MEX": [1, 2, 3], "EGY": [4, 1, 1], "ESP": [1, 2, 3],
    "ARG": [2, 3, 1], "POR": [1, 1, 4], "CZE": [2, 1, 4], "SUI": [1, 3, 3],
    "BRA": [4, 1, 2], "GER": [1, 2, 4], "IRN": [1, 4, 2], "NZL": [1, 2, 4],
    "URU": [1, 1, 5], "COL": [1, 1, 5], "ENG": [4, 2, 1], "CAN": [3, 1, 4],
    "BIH": [3, 4, 1], "MAR": [5, 2, 1], "USA": [3, 1, 4], "TUR": [1, 3, 4],
    "ECU": [2, 1, 5], "NED": [4, 3, 1], "JOR": [3, 2, 5], "AUT": [1, 5, 2],
    "SCO": [1, 2, 5], "KOR": [2, 4, 1], "RSA": [4, 2, 1], "FRA": [3, 1, 5],
    "NOR": [1, 2, 5], "ALG": [5, 1, 2], "SEN": [5, 2, 1], "PAR": [3, 4, 1],
    "JPN": [4, 3, 1], "QAT": [1, 3, 4], "SWE": [1, 4, 3], "CIV": [2, 5, 1],
    "TUN": [1, 4, 3], "HAI": [1, 5, 2], "AUS": [1, 4, 3], "GHA": [1, 4, 3],
    "PAN": [1, 3, 4], "CRO": [5, 1, 2], "COD": [5, 1, 1], "UZB": [1, 5, 1],
    "CPV": [5, 1, 2], "KSA": [1, 5, 2], "IRQ": [1, 5, 3], "CUW": [5, 2, 1],
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
    """Total FDR across 3 group stage games. Lower = easier fixtures."""
    fdr = FDR.get(team_code, [3, 3, 3])
    return sum(fdr)

def get_avg_cs_pct(team_code: str) -> float:
    """Average clean sheet probability across 3 group stage games."""
    cs = CS_PCT.get(team_code, [0.3, 0.3, 0.3])
    return sum(cs) / 3

def get_avg_proj_goals(team_code: str) -> float:
    """Average projected goals per game across 3 group stage games."""
    g = PROJ_GOALS.get(team_code, [1.0, 1.0, 1.0])
    return sum(g) / 3

def get_team_group(team_code: str) -> str:
    for grp, teams in GROUPS.items():
        if team_code in teams:
            return grp
    return "?"

def get_group_balance(team_code: str) -> str:
    grp = get_team_group(team_code)
    return GROUP_BALANCE.get(grp, "Unknown")
