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
# Transition state: 6 R16 matches are set (confirmed teams carry MD5/R16 data);
# 8 teams are still finishing their R32 games (carry R32 data until those results
# land). Eliminated teams are removed entirely.
CURRENT_ROUND = "R16"
CURRENT_ROUND_DATE = "03.07.26"

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

# Next opponent (3-letter code). Confirmed teams point to their R16 opponent;
# the 12 still-playing teams point to their (unfinished) R32 opponent.
FIXTURES = {
    # ── Confirmed Round of 16 matches (6) ──
    "FRA": "PAR", "PAR": "FRA",
    "CAN": "MAR", "MAR": "CAN",
    "POR": "ESP", "ESP": "POR",
    "USA": "BEL", "BEL": "USA",
    "BRA": "NOR", "NOR": "BRA",
    "MEX": "ENG", "ENG": "MEX",
    # ── Pending Round of 32 matches (still to play, feed the last 2 R16 slots) ──
    "ARG": "CPV", "CPV": "ARG",
    "AUS": "EGY", "EGY": "AUS",
    "SUI": "ALG", "ALG": "SUI",
    "COL": "GHA", "GHA": "COL",
}

# Projected goals for the upcoming match. Confirmed teams = MD5/R16 (FPLJoe,
# 02.07.26); still-playing teams = their R32 projection (build_r32.py).
PROJ_GOALS = {
    # Confirmed R16 (MD5 03.07)
    "FRA": 2.61, "PAR": 0.51, "CAN": 0.89, "MAR": 1.68, "POR": 1.13, "ESP": 1.75,
    "USA": 1.62, "BEL": 1.54, "BRA": 1.92, "NOR": 1.22, "MEX": 1.17, "ENG": 1.35,
    # Pending R32
    "ARG": 2.57, "CPV": 0.48, "AUS": 0.95, "EGY": 1.13, "SUI": 1.62, "ALG": 0.99,
    "COL": 1.61, "GHA": 0.71,
}

# Clean sheet probability for the upcoming match (same split as PROJ_GOALS).
CS_PCT = {
    # Confirmed R16 (MD5 03.07)
    "FRA": 0.61, "PAR": 0.05, "CAN": 0.18, "MAR": 0.42, "POR": 0.17, "ESP": 0.34,
    "USA": 0.22, "BEL": 0.21, "BRA": 0.31, "NOR": 0.15, "MEX": 0.26, "ENG": 0.32,
    # Pending R32
    "ARG": 0.62, "CPV": 0.08, "AUS": 0.32, "EGY": 0.39, "SUI": 0.37, "ALG": 0.2,
    "COL": 0.49, "GHA": 0.2,
}

# FDR for the upcoming match (1=easiest, 5=hardest).
# Banded by opponent threat = avg(opp_xGF, opp_CS%):
#   1 → threat <0.45   2 → 0.45–0.62   3 → 0.62–0.85   4 → 0.85–1.20   5 → >1.20
FDR = {
    # Confirmed R16
    "FRA": 1, "PAR": 5, "CAN": 4, "MAR": 2, "POR": 4, "ESP": 3,
    "USA": 4, "BEL": 4, "BRA": 3, "NOR": 4, "MEX": 3, "ENG": 3,
    # Pending R32
    "ARG": 1, "CPV": 5, "AUS": 3, "EGY": 3, "SUI": 2, "ALG": 4,
    "COL": 2, "GHA": 4,
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
# 400k Monte-Carlo of the FULL remaining bracket at the R32→R16 transition.
# Confirmed R16 teams: r16 = 1.0 (already through). Still-playing teams: r16 =
# P(win their R32). r32 = 1.0 for all (everyone reached R32). Confirmed R16 games
# use MD5 odds; pending R32 games use R32 odds; R16-pending + QF/SF/Final use the
# calibrated Elo (KO_VARIANCE_K). See EXP_GAMES for expected remaining matches.
QUAL_PROBS: dict[str, dict] = {
    # ── Confirmed R16 (r16 = 1.0) ──
    "FRA": {"r32": 1.0, "r16": 1.0, "qf": 0.8854, "sf": 0.6242, "f": 0.3601},
    "PAR": {"r32": 1.0, "r16": 1.0, "qf": 0.1146, "sf": 0.0474, "f": 0.0143},
    "CAN": {"r32": 1.0, "r16": 1.0, "qf": 0.3188, "sf": 0.0942, "f": 0.0297},
    "MAR": {"r32": 1.0, "r16": 1.0, "qf": 0.6812, "sf": 0.2342, "f": 0.0893},
    "POR": {"r32": 1.0, "r16": 1.0, "qf": 0.3633, "sf": 0.2124, "f": 0.1068},
    "ESP": {"r32": 1.0, "r16": 1.0, "qf": 0.6367, "sf": 0.4187, "f": 0.241},
    "USA": {"r32": 1.0, "r16": 1.0, "qf": 0.5179, "sf": 0.1726, "f": 0.0678},
    "BEL": {"r32": 1.0, "r16": 1.0, "qf": 0.4821, "sf": 0.1963, "f": 0.091},
    "BRA": {"r32": 1.0, "r16": 1.0, "qf": 0.6479, "sf": 0.386, "f": 0.2149},
    "NOR": {"r32": 1.0, "r16": 1.0, "qf": 0.3521, "sf": 0.1488, "f": 0.06},
    "MEX": {"r32": 1.0, "r16": 1.0, "qf": 0.4569, "sf": 0.1761, "f": 0.0705},
    "ENG": {"r32": 1.0, "r16": 1.0, "qf": 0.5431, "sf": 0.289, "f": 0.1545},
    # ── Pending R32 (r16 = P(win R32)) ──
    "ARG": {"r32": 1.0, "r16": 0.8873, "qf": 0.6674, "sf": 0.4686, "f": 0.2916},
    "CPV": {"r32": 1.0, "r16": 0.1127, "qf": 0.0504, "sf": 0.0186, "f": 0.0056},
    "AUS": {"r32": 1.0, "r16": 0.4541, "qf": 0.1247, "sf": 0.0496, "f": 0.0158},
    "EGY": {"r32": 1.0, "r16": 0.5459, "qf": 0.1575, "sf": 0.0665, "f": 0.0227},
    "SUI": {"r32": 1.0, "r16": 0.6458, "qf": 0.3362, "sf": 0.1372, "f": 0.0586},
    "ALG": {"r32": 1.0, "r16": 0.3542, "qf": 0.1579, "sf": 0.0563, "f": 0.0206},
    "COL": {"r32": 1.0, "r16": 0.7137, "qf": 0.3915, "sf": 0.1663, "f": 0.0737},
    "GHA": {"r32": 1.0, "r16": 0.2863, "qf": 0.1144, "sf": 0.0368, "f": 0.0116},
}

# Expected REMAINING matches per team from the same Monte-Carlo (next guaranteed
# game + every round they're simulated to advance to). Used for tournament_xpts
# instead of summing QUAL_PROBS, so already-played rounds aren't double-counted.
EXP_GAMES: dict[str, float] = {
    "FRA": 2.87, "PAR": 1.176, "CAN": 1.443, "MAR": 2.005, "POR": 1.682,
    "ESP": 2.296, "USA": 1.758, "BEL": 1.769, "BRA": 2.249, "NOR": 1.561,
    "MEX": 1.704, "ENG": 1.987, "ARG": 3.315, "CPV": 1.187, "AUS": 1.644,
    "EGY": 1.793, "SUI": 2.178, "ALG": 1.589, "COL": 2.345, "GHA": 1.449,
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
