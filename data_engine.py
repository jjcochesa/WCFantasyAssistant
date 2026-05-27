"""
WC Fantasy 2026 data engine.
- Fetches player list from FIFA Fantasy API (or demo data)
- Fetches international + club stats from API-Football
- Applies Bayesian shrinkage (adaptive K = max(3.0, 40/sqrt(games)))
- Participation floor 0.75 for established starters (>=8 intl appearances)
- Scores players using team-level projections (goals, CS%) from image data
"""

import json
import math
import os
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import requests

from scoring_rules import SCORING, SCOUT_OWNERSHIP_THRESHOLD, SCOUT_POINTS_THRESHOLD
from data.team_stats import (
    CS_PCT, PROJ_GOALS, FDR, TEAM_NAMES, FIXTURES,
    get_avg_cs_pct, get_avg_proj_goals, get_team_fdr_total, get_group_balance,
)

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
FIFA_FANTASY_BASE = "https://gaming.fifa.com/api/en/fantasy"

WC_2026_LEAGUE_ID = 1
WC_2026_SEASON = 2026
CLUB_SEASON = 2024

CACHE_DIR = "data/cache"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_name(name: str) -> str:
    """Accent-strip + lowercase + Turkish dotless-ı fix for cross-source matching."""
    name = name.lower().replace("ı", "i")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = key.replace("/", "_").replace("?", "_").replace("&", "_")[:120]
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _from_cache(key: str):
    p = _cache_path(key)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _to_cache(key: str, data) -> None:
    with open(_cache_path(key), "w") as f:
        json.dump(data, f, indent=2)


def _api_football_get(endpoint: str, params: dict) -> Optional[dict]:
    """Cached GET to API-Football. Returns None on any error."""
    cache_key = f"apifootball_{endpoint}_" + "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached
    if not API_FOOTBALL_KEY:
        return None
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    try:
        resp = requests.get(
            f"{API_FOOTBALL_BASE}/{endpoint}",
            headers=headers, params=params, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        _to_cache(cache_key, data)
        time.sleep(0.3)
        return data
    except Exception as e:
        print(f"[API-Football] {endpoint} {params}: {e}")
        return None


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class PlayerStats:
    matches: int = 0
    minutes: int = 0
    goals: float = 0.0
    assists: float = 0.0
    shots_on_target: float = 0.0
    chances_created: float = 0.0
    tackles: float = 0.0
    clean_sheets: int = 0
    saves: float = 0.0
    yellow_cards: float = 0.0
    red_cards: float = 0.0
    goals_conceded: float = 0.0
    penalties_saved: float = 0.0

    def rate(self, stat: str) -> float:
        """Per-match rate for a stat. Returns 0 if no matches."""
        if self.matches == 0:
            return 0.0
        return getattr(self, stat) / self.matches


@dataclass
class Player:
    id: str
    name: str
    position: str          # GK / DEF / MID / FWD
    team_code: str         # 3-letter country code (e.g. "BRA")
    club: str = ""
    price: float = 0.0
    ownership_pct: float = 0.0

    national_stats: PlayerStats = field(default_factory=PlayerStats)
    club_stats: PlayerStats = field(default_factory=PlayerStats)

    # Set by lineup fetcher (0.0–1.0, fraction of recent games started)
    starter_rate: float = 1.0

    # Filled by engine
    raw_intl_ppg: float = 0.0
    raw_club_ppg: float = 0.0
    shrunk_intl_ppg: float = 0.0
    shrunk_club_ppg: float = 0.0
    participation_mult: float = 1.0
    combined_ppg: float = 0.0
    xpts_per_match: float = 0.0
    xpts_group_stage: float = 0.0   # projected total for all 3 group games
    value: float = 0.0              # xpts_group_stage / price
    scout_flag: bool = False

    @property
    def team_name(self) -> str:
        return TEAM_NAMES.get(self.team_code, self.team_code)

    @property
    def is_differential(self) -> bool:
        return self.ownership_pct < SCOUT_OWNERSHIP_THRESHOLD


# ── FIFA Fantasy API ──────────────────────────────────────────────────────────

POSITION_MAP = {
    1: "GK", 2: "DEF", 3: "MID", 4: "FWD",
    "GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD",
    "Goalkeeper": "GK", "Defender": "DEF", "Midfielder": "MID",
    "Forward": "FWD", "Attacker": "FWD",
}

# Static 3-letter country code map for FIFA Fantasy API nationality field
NATIONALITY_TO_CODE = {
    "spain": "ESP", "germany": "GER", "brazil": "BRA", "france": "FRA",
    "portugal": "POR", "england": "ENG", "argentina": "ARG", "belgium": "BEL",
    "switzerland": "SUI", "netherlands": "NED", "mexico": "MEX", "norway": "NOR",
    "uruguay": "URU", "colombia": "COL", "austria": "AUT", "usa": "USA",
    "united states": "USA", "canada": "CAN", "ecuador": "ECU", "morocco": "MAR",
    "croatia": "CRO", "turkey": "TUR", "ivory coast": "CIV", "cote d'ivoire": "CIV",
    "japan": "JPN", "egypt": "EGY", "senegal": "SEN", "scotland": "SCO",
    "czech republic": "CZE", "czechia": "CZE", "south korea": "KOR",
    "republic of korea": "KOR", "sweden": "SWE", "algeria": "ALG",
    "paraguay": "PAR", "iran": "IRN", "islamic republic of iran": "IRN",
    "bosnia and herzegovina": "BIH", "ghana": "GHA", "australia": "AUS",
    "south africa": "RSA", "tunisia": "TUN", "dr congo": "COD",
    "democratic republic of the congo": "COD", "uzbekistan": "UZB", "panama": "PAN",
    "saudi arabia": "KSA", "new zealand": "NZL", "cape verde": "CPV",
    "qatar": "QAT", "jordan": "JOR", "haiti": "HAI", "iraq": "IRQ",
    "curacao": "CUW",
}


def _parse_team_code(raw: dict) -> str:
    """Extract 3-letter team code from a FIFA Fantasy player record."""
    for f in ("teamCode", "countryCode", "nationalityCode", "team_code"):
        val = raw.get(f, "")
        if val and len(val) <= 4:
            return val.upper()
    for f in ("teamName", "nationality", "countryName", "national_team"):
        val = (raw.get(f) or "").lower().strip()
        if val in NATIONALITY_TO_CODE:
            return NATIONALITY_TO_CODE[val]
    return ""


def fetch_fantasy_players(session_token: Optional[str] = None) -> list:
    """
    Load players from FIFA Fantasy API. Falls back to cache if no token.
    session_token: Bearer token from play.fifa.com browser DevTools (Authorization header).
    """
    cached = _from_cache("fifa_fantasy_players_raw")
    if cached is not None and not session_token:
        return _parse_fantasy_players(cached)

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (WC Fantasy Assistant)",
    }
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"

    # Try multiple known endpoint patterns
    endpoints = [
        f"{FIFA_FANTASY_BASE}/v2/players",
        f"{FIFA_FANTASY_BASE}/players",
        "https://play.fifa.com/json/fantasy/players.json",
        "https://play.fifa.com/fantasy/en/players",
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                _to_cache("fifa_fantasy_players_raw", data)
                return _parse_fantasy_players(data)
        except Exception:
            continue

    if cached:
        print("[FIFA Fantasy] Live fetch failed, using cached data.")
        return _parse_fantasy_players(cached)

    return []


def _parse_fantasy_players(data) -> list:
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("players") or data.get("data") or data.get("response") or []
    else:
        return []

    players = []
    for raw in raw_list:
        pos_raw = raw.get("position") or raw.get("positionId") or raw.get("pos") or "MID"
        position = POSITION_MAP.get(pos_raw, POSITION_MAP.get(str(pos_raw), "MID"))
        team_code = _parse_team_code(raw)
        if not team_code:
            continue

        # Price normalisation — API may return in 100k or 1M units
        price_raw = raw.get("price") or raw.get("cost") or raw.get("value") or 0
        price = float(price_raw)
        if price > 200:
            price /= 10  # convert from 100k units to millions

        players.append(Player(
            id=str(raw.get("id") or raw.get("playerId") or ""),
            name=raw.get("name") or raw.get("knownName") or raw.get("playerName") or "",
            position=position,
            team_code=team_code,
            club=raw.get("clubName") or raw.get("club") or "",
            price=price,
            ownership_pct=float(raw.get("ownership") or raw.get("ownershipPercent") or raw.get("selectedBy") or 0.0),
        ))
    return players


def load_players_from_json(path: str) -> list:
    """Load player data from a locally-exported JSON file."""
    with open(path) as f:
        return _parse_fantasy_players(json.load(f))


# ── Stats fetching ────────────────────────────────────────────────────────────

def _parse_stats(data: dict, team_id: Optional[int] = None) -> Optional[PlayerStats]:
    responses = data.get("response", [])
    if not responses:
        return None
    stats_list = responses[0].get("statistics", [])
    if not stats_list:
        return None

    s = stats_list[0]
    if team_id:
        for candidate in stats_list:
            if candidate.get("team", {}).get("id") == team_id:
                s = candidate
                break

    games = s.get("games", {})
    goals_d = s.get("goals", {})
    shots_d = s.get("shots", {})
    passes_d = s.get("passes", {})
    tackles_d = s.get("tackles", {})
    cards_d = s.get("cards", {})
    penalty_d = s.get("penalty", {})

    return PlayerStats(
        matches=games.get("appearences") or 0,
        minutes=games.get("minutes") or 0,
        goals=goals_d.get("total") or 0,
        assists=goals_d.get("assists") or 0,
        shots_on_target=shots_d.get("on") or 0,
        chances_created=passes_d.get("key") or 0,
        tackles=tackles_d.get("total") or 0,
        saves=games.get("saves") or 0,
        yellow_cards=cards_d.get("yellow") or 0,
        red_cards=cards_d.get("red") or 0,
        goals_conceded=goals_d.get("conceded") or 0,
        penalties_saved=penalty_d.get("saved") or 0,
    )


def fetch_stats_national(player_id: int) -> Optional[PlayerStats]:
    data = _api_football_get("players", {
        "id": player_id,
        "season": WC_2026_SEASON,
        "league": WC_2026_LEAGUE_ID,
    })
    return _parse_stats(data) if data else None


def fetch_stats_club(player_id: int) -> Optional[PlayerStats]:
    data = _api_football_get("players", {
        "id": player_id,
        "season": CLUB_SEASON,
    })
    return _parse_stats(data) if data else None


# ── PPG calculation per scoring rules ────────────────────────────────────────

def _s(action: str, pos: str) -> float:
    return SCORING.get(action, {}).get(pos, 0)


def calc_raw_ppg(stats: PlayerStats, pos: str, team_code: str = "", match_num: int = None) -> float:
    """
    Expected points per match from raw stats, using team-level CS/goal projections
    blended with individual stat rates.
    match_num: 0/1/2 for specific matchday, or None for average across 3 MDs.
    """
    if stats.matches == 0:
        return 0.0

    xpts = 0.0

    # Minutes: assume full game (+1 for playing + +1 for 60+ = +2 total)
    xpts += 2.0

    # Goals
    xpts += stats.rate("goals") * _s("goal", pos)

    # Assists
    xpts += stats.rate("assists") * _s("assist", pos)

    # Clean sheet — blend player historical rate with team market CS probability
    if pos in ("GK", "DEF", "MID"):
        hist_cs_rate = stats.rate("clean_sheets") if stats.matches > 0 else 0
        if team_code and team_code in CS_PCT:
            if match_num is not None:
                market_cs = CS_PCT[team_code][match_num]
            else:
                market_cs = sum(CS_PCT[team_code]) / 3
            # Weight toward market data (it's more accurate for specific opponents)
            cs_rate = 0.4 * hist_cs_rate + 0.6 * market_cs
        else:
            cs_rate = hist_cs_rate
        xpts += cs_rate * _s("clean_sheet_60", pos)

        # Goals conceded: only additional goals (after the 1st) cost points
        # Expected goals conceded = opponent's projected goals
        if pos in ("GK", "DEF") and team_code:
            fixtures = FIXTURES.get(team_code, [])
            if match_num is not None and match_num < len(fixtures):
                opp = fixtures[match_num]
                exp_gc = PROJ_GOALS.get(opp, [1.0, 1.0, 1.0])[match_num]
            elif team_code in PROJ_GOALS:
                # Average opponent projected goals
                opps = FIXTURES.get(team_code, [])
                exp_gc = sum(PROJ_GOALS.get(o, [1.0])[i] for i, o in enumerate(opps)) / max(len(opps), 1)
            else:
                exp_gc = stats.rate("goals_conceded")
            # -1 for each goal conceded after the first
            xpts += max(0, exp_gc - 1) * _s("goals_conceded_add", pos)

    # GK-specific
    if pos == "GK":
        xpts += stats.rate("saves") / 3 * _s("saves_per_3", pos)
        xpts += stats.rate("penalties_saved") * _s("penalty_save", pos)

    # MID-specific
    if pos == "MID":
        xpts += stats.rate("tackles") / 3 * _s("tackles_per_3", pos)
        xpts += stats.rate("chances_created") / 2 * _s("chances_per_2", pos)

    # FWD-specific
    if pos == "FWD":
        xpts += stats.rate("shots_on_target") / 2 * _s("shots_on_target_per_2", pos)

    # Yellow cards
    xpts += stats.rate("yellow_cards") * _s("yellow_card", pos)
    xpts += stats.rate("red_cards") * _s("red_card", pos)

    return max(0.0, xpts)


# ── Bayesian shrinkage ────────────────────────────────────────────────────────

def _adaptive_k(games: int) -> float:
    """K = max(3.0, 40.0 / sqrt(games)). Veterans get ~83% own-PPG at 34 games."""
    return max(3.0, 40.0 / math.sqrt(max(games, 1)))


def _shrink(raw_ppg: float, pos_mean: float, games: int) -> float:
    """Bayesian shrinkage toward position mean."""
    k = _adaptive_k(games)
    return (games * raw_ppg + k * pos_mean) / (games + k)


def _participation_floor(shrunk_ppg: float, intl_matches: int) -> tuple:
    """
    Apply 0.75 participation multiplier to players with <8 recent international appearances.
    Only for established starters (>=8 games) do we trust full projection.
    Returns (adjusted_ppg, multiplier).
    """
    if intl_matches >= 8:
        return shrunk_ppg, 1.0
    mult = 0.75
    return shrunk_ppg * mult, mult


# ── Two-phase build ───────────────────────────────────────────────────────────

def build_projections(players: list) -> pd.DataFrame:
    """
    Phase 1: compute position-average raw PPG from qualified players (>=5 intl games).
    Phase 2: per-player shrinkage + participation floor + combined score.
    Returns ranked DataFrame.
    """
    # Phase 1 — position means from qualified players
    pos_intl_ppg: dict = {p: [] for p in ["GK", "DEF", "MID", "FWD"]}
    pos_club_ppg: dict = {p: [] for p in ["GK", "DEF", "MID", "FWD"]}

    for p in players:
        if p.national_stats.matches >= 5:
            raw = calc_raw_ppg(p.national_stats, p.position, p.team_code)
            pos_intl_ppg[p.position].append(raw)
        if p.club_stats.matches >= 10:
            raw = calc_raw_ppg(p.club_stats, p.position)
            pos_club_ppg[p.position].append(raw)

    pos_intl_mean = {
        pos: (sum(vals) / len(vals)) if vals else _default_pos_mean(pos)
        for pos, vals in pos_intl_ppg.items()
    }
    pos_club_mean = {
        pos: (sum(vals) / len(vals)) if vals else _default_pos_mean(pos)
        for pos, vals in pos_club_ppg.items()
    }

    # Phase 2 — per-player records
    for p in players:
        p.raw_intl_ppg = calc_raw_ppg(p.national_stats, p.position, p.team_code)
        p.raw_club_ppg = calc_raw_ppg(p.club_stats, p.position)

        p.shrunk_intl_ppg = _shrink(p.raw_intl_ppg, pos_intl_mean[p.position], p.national_stats.matches)
        p.shrunk_club_ppg = _shrink(p.raw_club_ppg, pos_club_mean[p.position], p.club_stats.matches)

        shrunk_intl, p.participation_mult = _participation_floor(p.shrunk_intl_ppg, p.national_stats.matches)

        # Combined: 60% international + 40% club
        p.combined_ppg = 0.6 * shrunk_intl + 0.4 * p.shrunk_club_ppg

        # Starter weight: scale down bench players (0.4 floor so deep squad
        # members aren't zeroed out — they still might start at WC)
        starter_mult = max(0.4, p.starter_rate)
        p.xpts_per_match = round(p.combined_ppg * starter_mult, 3)

        # Group stage total: sum expected pts across 3 matchdays
        total = 0.0
        for md in range(3):
            intl_md = calc_raw_ppg(p.national_stats, p.position, p.team_code, match_num=md)
            shrunk_md = _shrink(intl_md, pos_intl_mean[p.position], p.national_stats.matches)
            shrunk_md_adj, _ = _participation_floor(shrunk_md, p.national_stats.matches)
            club_md = calc_raw_ppg(p.club_stats, p.position)
            shrunk_club_md = _shrink(club_md, pos_club_mean[p.position], p.club_stats.matches)
            combined_md = 0.6 * shrunk_md_adj + 0.4 * shrunk_club_md
            total += combined_md * starter_mult
        p.xpts_group_stage = round(total, 2)

        if p.price > 0:
            p.value = round(p.xpts_group_stage / p.price, 3)

        p.scout_flag = p.xpts_per_match > SCOUT_POINTS_THRESHOLD and p.is_differential

    return _to_dataframe(players)


def _default_pos_mean(pos: str) -> float:
    return {"GK": 4.5, "DEF": 4.0, "MID": 4.5, "FWD": 5.0}[pos]


def _to_dataframe(players: list) -> pd.DataFrame:
    rows = []
    for p in players:
        fdr_total = get_team_fdr_total(p.team_code)
        avg_cs = get_avg_cs_pct(p.team_code)
        avg_goals = get_avg_proj_goals(p.team_code)
        cs_vals = CS_PCT.get(p.team_code, ["-", "-", "-"])
        g_vals = PROJ_GOALS.get(p.team_code, ["-", "-", "-"])
        fdr_vals = FDR.get(p.team_code, ["-", "-", "-"])

        rows.append({
            "id": p.id,
            "name": p.name,
            "pos": p.position,
            "country": p.team_name,
            "team_code": p.team_code,
            "club": p.club,
            "price": p.price,
            "own_%": round(p.ownership_pct, 1),
            "xPts/game": p.xpts_per_match,
            "xPts_GS": p.xpts_group_stage,
            "value": p.value,
            "scout": p.scout_flag,
            "intl_games": p.national_stats.matches,
            "intl_goals": p.national_stats.goals,
            "intl_assists": p.national_stats.assists,
            "intl_cs": p.national_stats.clean_sheets,
            "intl_sot": round(p.national_stats.shots_on_target, 1),
            "intl_chances": round(p.national_stats.chances_created, 1),
            "intl_tackles": round(p.national_stats.tackles, 1),
            "intl_saves": round(p.national_stats.saves, 1),
            "club_games": p.club_stats.matches,
            "club_goals": p.club_stats.goals,
            "club_assists": p.club_stats.assists,
            "club_cs": p.club_stats.clean_sheets,
            "club_sot": round(p.club_stats.shots_on_target, 1),
            "club_chances": round(p.club_stats.chances_created, 1),
            "club_tackles": round(p.club_stats.tackles, 1),
            "club_saves": round(p.club_stats.saves, 1),
            "starter_%": round(p.starter_rate * 100),
            "raw_intl_ppg": round(p.raw_intl_ppg, 3),
            "raw_club_ppg": round(p.raw_club_ppg, 3),
            "participation_mult": p.participation_mult,
            "team_fdr": fdr_total,
            "avg_cs%": round(avg_cs * 100, 1),
            "avg_proj_goals": round(avg_goals, 2),
            "fdr_md1": fdr_vals[0], "fdr_md2": fdr_vals[1], "fdr_md3": fdr_vals[2],
            "cs_md1": f"{int(cs_vals[0]*100)}%" if isinstance(cs_vals[0], float) else cs_vals[0],
            "cs_md2": f"{int(cs_vals[1]*100)}%" if isinstance(cs_vals[1], float) else cs_vals[1],
            "cs_md3": f"{int(cs_vals[2]*100)}%" if isinstance(cs_vals[2], float) else cs_vals[2],
            "goals_md1": g_vals[0], "goals_md2": g_vals[1], "goals_md3": g_vals[2],
            "group_balance": get_group_balance(p.team_code),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("xPts_GS", ascending=False).reset_index(drop=True)
        df.index += 1
    return df


# ── Demo dataset ──────────────────────────────────────────────────────────────

def get_demo_players() -> list:
    """
    Realistic 40-player demo dataset spanning all 4 positions and top nations.
    Used when no API key is available.
    """
    return [
        # GK
        Player("1", "Thibaut Courtois", "GK", "BEL", "Real Madrid", 6.0, 18.0,
               PlayerStats(12, 1080, 0, 0, 0, 0, 0, 8, 42, 1, 0, 10, 1),
               PlayerStats(30, 2700, 0, 0, 0, 0, 0, 13, 88, 1, 0, 22, 2)),
        Player("2", "Alisson Becker", "GK", "BRA", "Liverpool", 5.5, 14.0,
               PlayerStats(10, 900, 0, 0, 0, 0, 0, 7, 28, 0, 0, 6, 0),
               PlayerStats(32, 2880, 0, 0, 0, 0, 0, 14, 85, 0, 0, 28, 0)),
        Player("3", "Emiliano Martinez", "GK", "ARG", "Aston Villa", 5.5, 12.0,
               PlayerStats(10, 900, 0, 0, 0, 0, 0, 6, 30, 1, 0, 9, 0),
               PlayerStats(33, 2970, 0, 0, 0, 0, 0, 11, 95, 2, 0, 38, 0)),
        Player("4", "Yann Sommer", "GK", "SUI", "Inter Milan", 4.5, 4.0,
               PlayerStats(8, 720, 0, 0, 0, 0, 0, 4, 22, 0, 0, 10, 0),
               PlayerStats(31, 2790, 0, 0, 0, 0, 0, 15, 78, 0, 0, 23, 0)),
        # DEF
        Player("10", "Virgil van Dijk", "DEF", "NED", "Liverpool", 7.0, 22.0,
               PlayerStats(10, 900, 2, 1, 0, 0, 20, 6, 0, 1, 0, 9, 0),
               PlayerStats(32, 2880, 3, 2, 0, 0, 55, 14, 0, 2, 0, 28, 0)),
        Player("11", "Achraf Hakimi", "DEF", "MAR", "PSG", 7.5, 28.0,
               PlayerStats(10, 900, 3, 4, 0, 0, 22, 5, 0, 2, 0, 8, 0),
               PlayerStats(30, 2700, 5, 8, 0, 0, 60, 10, 0, 3, 0, 25, 0)),
        Player("12", "Alejandro Grimaldo", "DEF", "ESP", "Bayer Leverkusen", 7.0, 25.0,
               PlayerStats(9, 810, 2, 3, 0, 0, 18, 5, 0, 1, 0, 7, 0),
               PlayerStats(32, 2880, 6, 12, 0, 0, 55, 11, 0, 2, 0, 20, 0)),
        Player("13", "Theo Hernandez", "DEF", "FRA", "AC Milan", 7.5, 20.0,
               PlayerStats(8, 720, 2, 2, 0, 0, 15, 4, 0, 2, 0, 6, 0),
               PlayerStats(28, 2520, 4, 7, 0, 0, 48, 9, 0, 4, 0, 22, 0)),
        Player("14", "Ruben Dias", "DEF", "POR", "Man City", 6.5, 9.0,
               PlayerStats(9, 810, 1, 0, 0, 0, 22, 6, 0, 2, 0, 7, 0),
               PlayerStats(30, 2700, 1, 1, 0, 0, 62, 13, 0, 2, 0, 24, 0)),
        Player("16", "William Saliba", "DEF", "FRA", "Arsenal", 6.0, 10.0,
               PlayerStats(9, 810, 1, 0, 0, 0, 25, 5, 0, 1, 0, 7, 0),
               PlayerStats(32, 2880, 2, 1, 0, 0, 70, 14, 0, 2, 0, 22, 0)),
        Player("17", "Nuno Mendes", "DEF", "POR", "PSG", 6.0, 8.0,
               PlayerStats(9, 810, 1, 2, 0, 0, 18, 5, 0, 1, 0, 8, 0),
               PlayerStats(27, 2430, 1, 4, 0, 0, 48, 9, 0, 2, 0, 20, 0)),
        Player("18", "Joao Cancelo", "DEF", "POR", "Barcelona", 6.5, 15.0,
               PlayerStats(9, 810, 1, 3, 0, 0, 20, 5, 0, 2, 0, 8, 0),
               PlayerStats(26, 2340, 2, 5, 0, 0, 52, 8, 0, 3, 0, 20, 0)),
        # MID
        Player("30", "Jude Bellingham", "MID", "ENG", "Real Madrid", 9.5, 45.0,
               PlayerStats(10, 900, 5, 3, 0, 18, 15, 0, 0, 2, 0, 0, 0),
               PlayerStats(30, 2700, 19, 10, 0, 48, 38, 0, 0, 4, 0, 0, 0)),
        Player("31", "Florian Wirtz", "MID", "GER", "Bayer Leverkusen", 9.0, 35.0,
               PlayerStats(10, 900, 4, 6, 0, 25, 10, 0, 0, 1, 0, 0, 0),
               PlayerStats(32, 2880, 12, 14, 0, 70, 22, 0, 0, 2, 0, 0, 0)),
        Player("32", "Pedri", "MID", "ESP", "Barcelona", 8.5, 30.0,
               PlayerStats(10, 900, 3, 5, 0, 22, 18, 0, 0, 1, 0, 0, 0),
               PlayerStats(28, 2520, 6, 8, 0, 55, 40, 0, 0, 3, 0, 0, 0)),
        Player("33", "Phil Foden", "MID", "ENG", "Man City", 8.5, 25.0,
               PlayerStats(9, 810, 4, 3, 0, 20, 8, 0, 0, 0, 0, 0, 0),
               PlayerStats(30, 2700, 14, 11, 0, 58, 18, 0, 0, 2, 0, 0, 0)),
        Player("34", "Declan Rice", "MID", "ENG", "Arsenal", 7.5, 20.0,
               PlayerStats(10, 900, 2, 2, 0, 14, 30, 0, 0, 2, 0, 0, 0),
               PlayerStats(32, 2880, 7, 8, 0, 45, 82, 0, 0, 4, 0, 0, 0)),
        Player("35", "Nico Williams", "MID", "ESP", "Athletic Bilbao", 7.5, 22.0,
               PlayerStats(10, 900, 3, 5, 0, 24, 12, 0, 0, 1, 0, 0, 0),
               PlayerStats(30, 2700, 10, 12, 0, 60, 28, 0, 0, 2, 0, 0, 0)),
        Player("36", "Vitinha", "MID", "POR", "PSG", 7.5, 12.0,
               PlayerStats(10, 900, 2, 4, 0, 20, 22, 0, 0, 1, 0, 0, 0),
               PlayerStats(30, 2700, 4, 8, 0, 52, 55, 0, 0, 3, 0, 0, 0)),
        Player("37", "Granit Xhaka", "MID", "SUI", "Bayer Leverkusen", 6.5, 4.0,
               PlayerStats(10, 900, 2, 3, 0, 16, 28, 0, 0, 3, 0, 0, 0),
               PlayerStats(30, 2700, 3, 5, 0, 38, 72, 0, 0, 5, 0, 0, 0)),
        Player("38", "Alexis Mac Allister", "MID", "ARG", "Liverpool", 7.5, 18.0,
               PlayerStats(10, 900, 3, 3, 0, 16, 25, 0, 0, 2, 0, 0, 0),
               PlayerStats(30, 2700, 6, 7, 0, 42, 60, 0, 0, 3, 0, 0, 0)),
        Player("39", "Luka Modric", "MID", "CRO", "Real Madrid", 6.5, 8.0,
               PlayerStats(8, 720, 1, 3, 0, 18, 20, 0, 0, 1, 0, 0, 0),
               PlayerStats(22, 1980, 3, 6, 0, 40, 35, 0, 0, 2, 0, 0, 0)),
        # FWD
        Player("50", "Kylian Mbappe", "FWD", "FRA", "Real Madrid", 12.0, 60.0,
               PlayerStats(10, 900, 8, 3, 28, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(30, 2700, 25, 8, 80, 0, 0, 0, 0, 2, 0, 0, 0)),
        Player("51", "Erling Haaland", "FWD", "NOR", "Man City", 11.5, 40.0,
               PlayerStats(8, 720, 7, 2, 22, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(26, 2340, 22, 5, 72, 0, 0, 0, 0, 1, 0, 0, 0)),
        Player("52", "Harry Kane", "FWD", "ENG", "Bayern Munich", 10.5, 35.0,
               PlayerStats(10, 900, 7, 3, 24, 0, 0, 0, 0, 0, 0, 0, 0),
               PlayerStats(32, 2880, 30, 8, 88, 0, 0, 0, 0, 1, 0, 0, 0)),
        Player("53", "Lamine Yamal", "FWD", "ESP", "Barcelona", 10.5, 38.0,
               PlayerStats(10, 900, 5, 6, 20, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(32, 2880, 14, 15, 62, 0, 0, 0, 0, 2, 0, 0, 0)),
        Player("54", "Vinicius Jr", "FWD", "BRA", "Real Madrid", 11.0, 45.0,
               PlayerStats(10, 900, 6, 4, 25, 0, 0, 0, 0, 2, 0, 0, 0),
               PlayerStats(28, 2520, 18, 9, 68, 0, 0, 0, 0, 4, 0, 0, 0)),
        Player("55", "Bukayo Saka", "FWD", "ENG", "Arsenal", 9.5, 28.0,
               PlayerStats(10, 900, 4, 5, 18, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(32, 2880, 16, 14, 58, 0, 0, 0, 0, 2, 0, 0, 0)),
        Player("57", "Richarlison", "FWD", "BRA", "Tottenham", 7.5, 4.2,
               PlayerStats(9, 810, 5, 2, 20, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(22, 1980, 10, 3, 42, 0, 0, 0, 0, 2, 0, 0, 0)),
        Player("58", "Memphis Depay", "FWD", "NED", "Atletico Madrid", 7.5, 4.5,
               PlayerStats(9, 810, 5, 2, 18, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(25, 2250, 12, 4, 48, 0, 0, 0, 0, 3, 0, 0, 0)),
        # Budget DEF fillers
        Player("61", "Lucas Digne", "DEF", "FRA", "Aston Villa", 4.5, 2.0,
               PlayerStats(6, 540, 0, 1, 0, 0, 10, 2, 0, 1, 0, 5, 0),
               PlayerStats(24, 2160, 2, 5, 0, 0, 42, 8, 0, 3, 0, 18, 0)),
        Player("62", "Jonathan Tah", "DEF", "GER", "Bayer Leverkusen", 4.5, 1.5,
               PlayerStats(7, 630, 0, 0, 0, 0, 15, 3, 0, 1, 0, 4, 0),
               PlayerStats(28, 2520, 1, 1, 0, 0, 55, 12, 0, 4, 0, 20, 0)),
        # Budget MID filler
        Player("63", "Sofyan Amrabat", "MID", "MAR", "Fiorentina", 5.0, 2.5,
               PlayerStats(8, 720, 0, 1, 0, 8, 30, 0, 0, 3, 0, 0, 0),
               PlayerStats(28, 2520, 1, 2, 0, 22, 88, 0, 0, 7, 0, 0, 0)),
        # Budget FWD fillers
        Player("64", "Santiago Gimenez", "FWD", "MEX", "Feyenoord", 5.5, 3.0,
               PlayerStats(8, 720, 4, 1, 14, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(28, 2520, 18, 4, 62, 0, 0, 0, 0, 2, 0, 0, 0)),
        Player("65", "Jhon Duran", "FWD", "COL", "Aston Villa", 5.5, 2.8,
               PlayerStats(7, 420, 3, 0, 10, 0, 0, 0, 0, 1, 0, 0, 0),
               PlayerStats(26, 1560, 12, 2, 38, 0, 0, 0, 0, 3, 0, 0, 0)),
        Player("66", "Chris Wood", "FWD", "NZL", "Nottm Forest", 5.0, 1.2,
               PlayerStats(6, 540, 3, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0),
               PlayerStats(30, 2700, 14, 2, 50, 0, 0, 0, 0, 2, 0, 0, 0)),
    ]


WC_SQUADS_FILE = "data/wc_squads.json"

# Default price estimates by position (used when FIFA Fantasy prices not available)
_DEFAULT_PRICE = {"GK": 5.0, "DEF": 5.5, "MID": 7.0, "FWD": 8.0}


def load_from_wc_squads() -> list:
    """
    Load real player pool from data/wc_squads.json (generated by fetch_wc_data.py).
    Returns Player objects with starter_rate set but no prices (use defaults).
    """
    if not os.path.exists(WC_SQUADS_FILE):
        return []
    try:
        with open(WC_SQUADS_FILE) as f:
            data = json.load(f)
    except Exception:
        return []

    players = []
    seen_ids: set[str] = set()
    for team_code, team_data in data.get("teams", {}).items():
        if team_code not in TEAM_NAMES:
            continue
        game_count = team_data.get("lineup_games_sampled", 0)
        for idx, p in enumerate(team_data.get("players", [])):
            pid = p.get("id") or f"{team_code}_{idx}"
            if pid in seen_ids:
                continue
            seen_ids.add(pid)

            pos = p.get("position", "MID")
            starts = p.get("starts") or 0
            starter_rate = p.get("starter_rate")
            if starter_rate is None:
                # No lineup data — give bench players a low default
                starter_rate = 0.5 if starts == 0 else min(starts / max(game_count, 1), 1.0)

            # Build PlayerStats from pre-fetched intl stats if available
            intl = p.get("intl_stats") or {}
            nat_stats = PlayerStats(
                matches=intl.get("matches", 0),
                minutes=intl.get("minutes", 0),
                goals=intl.get("goals", 0),
                assists=intl.get("assists", 0),
                shots_on_target=intl.get("shots_on_target", 0),
                chances_created=intl.get("chances_created", 0),
                tackles=intl.get("tackles", 0),
                saves=intl.get("saves", 0),
                yellow_cards=intl.get("yellow_cards", 0),
                red_cards=intl.get("red_cards", 0),
                goals_conceded=intl.get("goals_conceded", 0),
                penalties_saved=intl.get("penalties_saved", 0),
            )

            players.append(Player(
                id=pid,
                name=p.get("name", "Unknown"),
                position=pos,
                team_code=team_code,
                club="",
                price=_DEFAULT_PRICE.get(pos, 6.0),
                ownership_pct=0.0,
                national_stats=nat_stats,
                starter_rate=float(starter_rate),
            ))
    return players


def load_data(
    session_token: Optional[str] = None,
    players_file: Optional[str] = None,
    use_demo: bool = False,
    enrich_with_api: bool = True,
) -> pd.DataFrame:
    """Main entry point. Fetches players + stats, returns ranked DataFrame."""
    if use_demo:
        players = get_demo_players()
    elif players_file:
        players = load_players_from_json(players_file)
    else:
        # Priority: FIFA Fantasy API → wc_squads.json → demo
        players = fetch_fantasy_players(session_token)
        if not players:
            players = load_from_wc_squads()
        if not players:
            players = get_demo_players()

    if enrich_with_api and API_FOOTBALL_KEY and not use_demo:
        _enrich_stats(players)

    return build_projections(players)


def _enrich_stats(players: list) -> None:
    print(f"Enriching {len(players)} players with API-Football stats...")
    for i, p in enumerate(players):
        if not p.id or not p.id.isdigit():
            continue
        try:
            nat = fetch_stats_national(int(p.id))
            if nat:
                p.national_stats = nat
            club = fetch_stats_club(int(p.id))
            if club:
                p.club_stats = club
        except Exception as e:
            print(f"  Skipping {p.name}: {e}")
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(players)} done")
