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
    "ESP": [3.27, 2.83, 1.82], "GER": [3.99, 1.88, 1.79], "BRA": [1.78, 3.64, 2.14],
    "FRA": [1.98, 2.82, 1.72], "POR": [2.37, 2.55, 1.48], "ENG": [1.67, 2.19, 2.53],
    "ARG": [1.96, 1.71, 2.63], "BEL": [1.79, 1.97, 2.40], "SUI": [2.29, 1.77, 1.44],
    "NED": [1.55, 1.67, 1.82], "MEX": [1.83, 1.49, 1.47], "NOR": [2.42, 1.49, 0.84],
    "URU": [1.89, 1.95, 0.87], "COL": [1.94, 1.73, 1.03], "AUT": [2.25, 0.80, 1.42],
    "USA": [1.50, 1.63, 1.32], "CAN": [1.55, 1.78, 1.07], "ECU": [1.17, 2.29, 0.92],
    "MAR": [0.86, 1.31, 2.17], "CRO": [0.88, 1.86, 1.56], "TUR": [1.56, 1.27, 1.21],
    "CIV": [0.91, 0.91, 2.22], "JPN": [1.12, 1.43, 1.44], "EGY": [0.97, 1.57, 1.22],
    "SEN": [0.78, 1.12, 1.83], "SCO": [2.01, 0.95, 0.70], "CZE": [1.15, 1.35, 0.99],
    "KOR": [1.17, 0.87, 1.38], "SWE": [1.44, 0.89, 1.07], "ALG": [0.65, 1.67, 1.02],
    "PAR": [1.02, 0.99, 1.33], "IRN": [1.50, 0.70, 1.03], "BIH": [0.91, 0.75, 1.57],
    "GHA": [1.46, 0.68, 0.84], "AUS": [0.92, 0.88, 0.98], "RSA": [0.68, 0.90, 1.02],
    "TUN": [0.90, 0.88, 0.78], "COD": [0.66, 0.62, 1.17], "UZB": [0.67, 0.60, 1.08],
    "PAN": [1.01, 0.70, 0.63], "KSA": [0.74, 0.38, 1.17], "NZL": [0.89, 0.73, 0.61],
    "CPV": [0.41, 0.71, 1.08], "QAT": [0.65, 0.63, 0.88], "JOR": [0.74, 0.83, 0.54],
    "HAI": [0.72, 0.53, 0.67], "IRQ": [0.58, 0.43, 0.73], "CUW": [0.37, 0.56, 0.61],
}

# Clean sheet probability per matchday [MD1, MD2, MD3] — FPLJoe.com (from betting markets)
CS_PCT = {
    "ESP": [0.67, 0.69, 0.42], "ARG": [0.52, 0.45, 0.59], "FRA": [0.46, 0.65, 0.43],
    "BRA": [0.42, 0.59, 0.50], "GER": [0.69, 0.40, 0.40], "ENG": [0.41, 0.51, 0.53],
    "POR": [0.52, 0.55, 0.36], "BEL": [0.38, 0.50, 0.55], "SUI": [0.52, 0.47, 0.34],
    "MEX": [0.51, 0.42, 0.37], "COL": [0.51, 0.54, 0.23], "NED": [0.33, 0.41, 0.46],
    "CAN": [0.40, 0.53, 0.24], "ECU": [0.40, 0.57, 0.17], "URU": [0.48, 0.49, 0.16],
    "CRO": [0.19, 0.50, 0.43], "USA": [0.36, 0.42, 0.30], "MAR": [0.17, 0.39, 0.51],
    "NOR": [0.56, 0.33, 0.18], "TUR": [0.40, 0.37, 0.27], "AUT": [0.48, 0.18, 0.36],
    "CIV": [0.31, 0.15, 0.55], "EGY": [0.17, 0.48, 0.36], "JPN": [0.21, 0.42, 0.34],
    "CZE": [0.31, 0.41, 0.23], "KOR": [0.32, 0.23, 0.36], "SCO": [0.49, 0.27, 0.12],
    "IRN": [0.41, 0.14, 0.30], "SEN": [0.14, 0.23, 0.48], "SWE": [0.41, 0.19, 0.24],
    "ALG": [0.14, 0.44, 0.24], "BIH": [0.21, 0.17, 0.42], "GHA": [0.36, 0.11, 0.21],
    "RSA": [0.16, 0.26, 0.25], "AUS": [0.21, 0.19, 0.26], "TUN": [0.24, 0.24, 0.16],
    "COD": [0.09, 0.18, 0.34], "KSA": [0.15, 0.06, 0.34], "UZB": [0.14, 0.08, 0.31],
    "NZL": [0.22, 0.21, 0.09], "CPV": [0.04, 0.14, 0.31], "QAT": [0.10, 0.17, 0.21],
    "PAN": [0.23, 0.16, 0.08], "JOR": [0.11, 0.19, 0.07], "HAI": [0.13, 0.03, 0.11],
    "IRQ": [0.09, 0.06, 0.16], "CUW": [0.02, 0.10, 0.11],
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
