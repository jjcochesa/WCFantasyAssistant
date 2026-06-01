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
try:
    from data.predicted_lineups import PREDICTED_XI, STARTER_MINUTES, BENCH_MINUTES
except Exception:
    PREDICTED_XI, STARTER_MINUTES, BENCH_MINUTES = {}, 70, 20
from data.team_stats import (
    CS_PCT, PROJ_GOALS, FDR, TEAM_NAMES, FIXTURES,
    get_avg_cs_pct, get_avg_proj_goals, get_team_fdr_total, get_group_balance,
    get_team_proj, get_opponent_xg,
)
try:
    from data.set_pieces import SET_PIECES
except Exception:
    SET_PIECES = {}

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
FIFA_FANTASY_BASE = "https://gaming.fifa.com/api/en/fantasy"

WC_2026_LEAGUE_ID = 1
WC_2026_SEASON = 2026
CLUB_SEASON = 2024

CACHE_DIR = "data/cache"
STATS_PATH        = "data/stats.json"           # primary — output of fetch_player_stats.py
FBREF_MAP_PATH    = "data/fbref_player_map.json"
MANUAL_STATS_PATH = "data/manual_stats.json"    # legacy fallback
MANUAL_NT_PATH    = "data/manual_nt_stats.json" # legacy fallback

# FBref/manual stats keyed two ways for fast lookup
_FBREF_BY_ID:   dict[str, dict] = {}  # fifa_player_id -> stats
_FBREF_BY_NAME: dict[str, dict] = {}  # norm_name      -> club stats
_NT_BY_NAME:    dict[str, dict] = {}  # norm_name      -> NT per-90 stats


def _load_fbref_map() -> None:
    global _FBREF_BY_ID, _FBREF_BY_NAME, _NT_BY_NAME

    # 1. Primary: data/stats.json — output of fetch_player_stats.py
    #    Format: {norm_name: {name, club: {...}, nt: {...}}}
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH) as f:
                stats_data: dict[str, dict] = json.load(f)
            club_count = nt_count = 0
            for norm_key, entry in stats_data.items():
                # stats.json keys use fetch_player_stats.norm() (applies aliases like
                # "vinicius jr"→"vinicius junior"). The app looks up by _norm_name(),
                # so also index under _norm_name(display name) to bridge the two.
                display = entry.get("name", "")
                alt_key = _norm_name(display) if display else None
                if "club" in entry:
                    _FBREF_BY_NAME[norm_key] = entry["club"]
                    if alt_key and alt_key not in _FBREF_BY_NAME:
                        _FBREF_BY_NAME[alt_key] = entry["club"]
                    club_count += 1
                if "nt" in entry:
                    _NT_BY_NAME[norm_key] = entry["nt"]
                    if alt_key and alt_key not in _NT_BY_NAME:
                        _NT_BY_NAME[alt_key] = entry["nt"]
                    nt_count += 1
            print(f"[Stats] Loaded {club_count} club + {nt_count} NT records from stats.json")
        except Exception as e:
            print(f"[Stats] Could not load stats.json: {e}")

    # 2. Legacy: manual_stats.json — fills gaps not covered by stats.json
    if os.path.exists(MANUAL_STATS_PATH):
        try:
            with open(MANUAL_STATS_PATH) as f:
                manual: dict[str, dict] = json.load(f)
            added = 0
            for norm_key, stats in manual.items():
                if norm_key not in _FBREF_BY_NAME:
                    if "norm_name" not in stats:
                        stats["norm_name"] = norm_key
                    _FBREF_BY_NAME[norm_key] = stats
                    added += 1
            if added:
                print(f"[Stats] +{added} club records from manual_stats.json (legacy)")
        except Exception as e:
            print(f"[Stats] Could not load manual_stats.json: {e}")

    # 3. Legacy: manual_nt_stats.json — fills NT gaps
    if os.path.exists(MANUAL_NT_PATH):
        try:
            with open(MANUAL_NT_PATH) as f:
                nt_data: dict[str, dict] = json.load(f)
            added = 0
            for norm_key, stats in nt_data.items():
                if norm_key not in _NT_BY_NAME:
                    _NT_BY_NAME[norm_key] = stats
                    added += 1
            if added:
                print(f"[Stats] +{added} NT records from manual_nt_stats.json (legacy)")
        except Exception as e:
            print(f"[Stats] Could not load manual_nt_stats.json: {e}")

    # 4. Load name_match output (may override manual with fresher data)
    if os.path.exists(FBREF_MAP_PATH):
        try:
            with open(FBREF_MAP_PATH) as f:
                data: dict[str, dict] = json.load(f)
            count = 0
            for key, stats in data.items():
                if key.isdigit():
                    _FBREF_BY_ID[key] = stats
                else:
                    _FBREF_BY_NAME[key] = stats
                nn = stats.get("norm_name", "")
                if nn:
                    _FBREF_BY_NAME[nn] = stats
                count += 1
            if count:
                print(f"[Stats] Loaded {count} records from fbref_player_map.json")
        except Exception as e:
            print(f"[Stats] Could not load fbref_player_map.json: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_name(name: str) -> str:
    """Accent-strip + lowercase for cross-source matching.
    Handles chars with no Unicode decomposition (ø→o, æ→ae, ß→ss) explicitly."""
    name = name.lower().replace("ı", "i").replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


# Display-name aliases for matching our roster names to the FIFA feed's names.
# Keys/values are in _match_key space (punctuation-stripped, lowercased).
# e.g. our "Vinicius Jr" and FIFA's "Vinícius Júnior" both resolve to "vinicius junior".
_LIVE_NAME_ALIASES = {
    "vinicius jr":      "vinicius junior",
    "savinho":          "savio",
    "gabriel jesus":    "gabriel jesus",
    "rodri":            "rodrigo hernandez",
}


def _match_key(name: str) -> str:
    """Stronger cross-source key: norm + strip punctuation + alias canonicalisation.
    Used on BOTH sides of the live-ownership overlay so name-format differences
    (Jr vs Júnior, hyphens, dots) don't drop matches."""
    n = _norm_name(name).replace("-", " ").replace(".", "").replace("'", "")
    n = " ".join(n.split())
    return _LIVE_NAME_ALIASES.get(n, n)


# Load stats maps now that _norm_name is defined (loader uses it for alias bridging)
_load_fbref_map()


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

    # Per-90 stats (blended: 65% NT / 35% club if NT >= 5 apps, else flipped)
    xg90: float = 0.0
    xa90: float = 0.0
    sot90: float = 0.0
    kp90: float = 0.0
    tackles90: float = 0.0
    save_rate: float = 0.7

    # Raw per-90 split by source (for separate club / NT display tabs)
    xg90_club: float = 0.0
    xa90_club: float = 0.0
    sot90_club: float = 0.0
    kp90_club: float = 0.0
    tackles90_club: float = 0.0

    xg90_nt: float = 0.0
    xa90_nt: float = 0.0
    sot90_nt: float = 0.0
    kp90_nt: float = 0.0
    tackles90_nt: float = 0.0

    # Computed by engine
    xpts_per_match: float = 0.0
    xpts_group_stage: float = 0.0
    value: float = 0.0
    scout_flag: bool = False
    starter_rate: float = 1.0  # FBref starts/mp (1.0 = unknown)
    projected_minutes: float = 90.0  # set from predicted XI or starter_rate
    predicted_starter: bool = False  # True if named in a predicted XI

    # Set-piece role bonuses (per-90 xG/xA, added flat in projection)
    sp_pk_xg: float = 0.0
    sp_fk_xg: float = 0.0
    sp_ck_xa: float = 0.0
    sp_roles: str = ""   # display, e.g. "PK·CK"
    _sample_minutes: float = 0.0  # effective minutes behind the blended per-90s

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

# FIFA Fantasy team ID → 3-letter code (from play.fifa.com/json/fantasy/squads.json)
FIFA_TEAM_ID_TO_CODE: dict[int, str] = {
    1: "ALG",  2: "ARG",  3: "AUS",  4: "AUT",  5: "BEL",  6: "BIH",
    7: "BRA",  8: "CPV",  9: "CAN", 10: "COL", 11: "COD", 12: "CIV",
   13: "CRO", 14: "CUW", 15: "CZE", 16: "ECU", 17: "EGY", 18: "ENG",
   19: "FRA", 20: "GER", 21: "GHA", 22: "HAI", 23: "IRN", 24: "IRQ",
   25: "JPN", 26: "JOR", 27: "KOR", 28: "MEX", 29: "MAR", 30: "NED",
   31: "NZL", 32: "NOR", 33: "PAN", 34: "PAR", 35: "POR", 36: "QAT",
   37: "KSA", 38: "SCO", 39: "SEN", 40: "RSA", 41: "ESP", 42: "SWE",
   43: "SUI", 44: "TUN", 45: "TUR", 46: "URU", 47: "USA", 48: "UZB",
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
    # Most reliable: FIFA internal team ID
    for f in ("teamId", "team_id", "squadId", "squad_id"):
        tid = raw.get(f)
        if isinstance(tid, int) and tid in FIFA_TEAM_ID_TO_CODE:
            return FIFA_TEAM_ID_TO_CODE[tid]
    # Fallback: explicit code fields
    for f in ("teamCode", "countryCode", "nationalityCode", "team_code", "abbr"):
        val = raw.get(f, "")
        if val and len(val) <= 4:
            return str(val).upper()
    # Last resort: name lookup
    for f in ("teamName", "nationality", "countryName", "national_team"):
        val = (raw.get(f) or "").lower().strip()
        if val in NATIONALITY_TO_CODE:
            return NATIONALITY_TO_CODE[val]
    return ""


FIFA_PLAYERS_URL = "https://play.fifa.com/json/fantasy/players.json"
FIFA_SQUADS_URL  = "https://play.fifa.com/json/fantasy/squads.json"

_FIFA_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Referer": "https://play.fifa.com/fantasy/",
}


def fetch_live_player_data(session_token: Optional[str] = None) -> dict:
    """
    Fetch live ownership % AND prices for all players from the FIFA Fantasy API.
    Never uses file cache — always hits live so the 5% scout threshold and
    squad builder budget use real numbers, not estimates.

    Returns {key: {"own_pct": float, "price": float}} where key is either
    the norm_name string or str(player_id). Both keys are added per player
    so lookups work whether we match by name or ID.

    Falls back to {} silently if the API is unreachable.
    """
    headers = dict(_FIFA_HEADERS)
    if session_token:
        token = session_token if session_token.startswith("Bearer") else f"Bearer {session_token}"
        headers["Authorization"] = token

    for url in [FIFA_PLAYERS_URL, f"{FIFA_FANTASY_BASE}/v2/players", f"{FIFA_FANTASY_BASE}/v1/players"]:
        try:
            raw_bytes = _fetch_url_timed(url, headers, wall_secs=8)
            if raw_bytes is None:
                continue
            data = json.loads(raw_bytes)
            raw_list = data if isinstance(data, list) else (
                data.get("players") or data.get("data") or data.get("response") or []
            )
            result: dict = {}
            for raw in raw_list:
                own = float(
                    raw.get("percentSelected") or raw.get("ownershipPercent") or
                    raw.get("selectedBy") or raw.get("ownership") or 0.0
                )
                # Price: stored in millions; divide if suspiciously large (>200)
                price_raw = float(raw.get("price") or raw.get("value") or raw.get("cost") or 0.0)
                price = price_raw / 10 if price_raw > 200 else price_raw

                pid = str(raw.get("id") or raw.get("playerId") or "")
                known = raw.get("knownName")
                if known:
                    name = known
                else:
                    first = raw.get("firstName") or ""
                    last  = raw.get("lastName") or ""
                    name  = f"{first} {last}".strip()

                entry = {"own_pct": own, "price": price}
                if pid:
                    result[pid] = entry
                if name:
                    result[_norm_name(name)] = entry
                    result[_match_key(name)] = entry  # alias-aware fallback key

            if result:
                print(f"[FIFA] Live data fetched: {len(raw_list)} players")
                return result
        except Exception as e:
            print(f"[FIFA] Live data fetch failed ({url}): {e}")
    return {}


# Keep old name as alias so nothing else breaks
def fetch_ownership_map(session_token: Optional[str] = None) -> dict:
    return fetch_live_player_data(session_token)


def _fetch_url_timed(url: str, headers: dict, wall_secs: int = 10) -> Optional[bytes]:
    """
    Fetch a URL with a hard wall-clock deadline.
    requests.get(timeout=N) only resets on each received chunk, so a slow
    server that trickles data can hang for minutes.  This wraps the call in
    a daemon thread and joins with a real clock limit.
    Returns raw bytes on success, None on timeout or error.
    """
    import threading
    bucket: dict = {}

    def _do():
        try:
            r = requests.get(
                url, headers=headers,
                timeout=(5, wall_secs),   # connect=5s, read=wall_secs per chunk
            )
            bucket["status"] = r.status_code
            bucket["content"] = r.content
        except Exception as exc:
            bucket["error"] = str(exc)

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    t.join(timeout=wall_secs + 2)          # hard wall deadline

    if t.is_alive():
        print(f"[FIFA Fantasy] Hard timeout ({wall_secs}s) on {url}")
        return None
    if bucket.get("status") != 200:
        print(f"[FIFA Fantasy] {url} → {bucket.get('status') or bucket.get('error')}")
        return None
    return bucket.get("content")


def fetch_fantasy_players(session_token: Optional[str] = None) -> list:
    """
    Load players from the public FIFA Fantasy JSON endpoint.
    Returns confirmed squad data — positions, prices, and ownership as
    registered in the live game.  Falls back to local file cache, then [].
    """
    cached = _from_cache("fifa_fantasy_players_raw")
    headers = dict(_FIFA_HEADERS)

    for url in [FIFA_PLAYERS_URL, f"{FIFA_FANTASY_BASE}/v2/players"]:
        raw_bytes = _fetch_url_timed(url, headers, wall_secs=10)
        if raw_bytes is None:
            continue
        try:
            data = json.loads(raw_bytes)
            _to_cache("fifa_fantasy_players_raw", data)
            print(f"[FIFA Fantasy] Loaded {_count_players(data)} players from {url}")
            return _parse_fantasy_players(data)
        except Exception as e:
            print(f"[FIFA Fantasy] Parse error ({url}): {e}")
            continue

    if cached:
        print("[FIFA Fantasy] Using cached player data (API unavailable).")
        return _parse_fantasy_players(cached)

    return []


def _count_players(data) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in ("players", "data", "response"):
            v = data.get(k)
            if isinstance(v, list):
                return len(v)
    return 0


def _parse_fantasy_players(data) -> list:
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("players") or data.get("data") or data.get("response") or []
    else:
        return []

    players = []
    for raw in raw_list:
        if raw.get("status") == "transferred":
            continue

        pos_raw = raw.get("position") or raw.get("positionId") or raw.get("pos") or "MID"
        position = POSITION_MAP.get(pos_raw, POSITION_MAP.get(str(pos_raw), "MID"))
        team_code = _parse_team_code(raw)
        if not team_code:
            continue

        # Name: knownName (display alias) if set, else firstName + lastName
        known = raw.get("knownName")
        if known:
            name = known
        else:
            first = raw.get("firstName") or raw.get("name") or ""
            last = raw.get("lastName") or ""
            name = f"{first} {last}".strip() or raw.get("playerName") or ""

        # Price: players.json already in millions; only divide if suspiciously large
        price_raw = raw.get("price") or raw.get("cost") or raw.get("value") or 0
        price = float(price_raw)
        if price > 200:
            price /= 10

        # Ownership: real field is percentSelected
        ownership = float(
            raw.get("percentSelected") or raw.get("ownership") or
            raw.get("ownershipPercent") or raw.get("selectedBy") or 0.0
        )

        players.append(Player(
            id=str(raw.get("id") or raw.get("playerId") or ""),
            name=name,
            position=position,
            team_code=team_code,
            club=raw.get("clubName") or raw.get("club") or "",
            price=price,
            ownership_pct=ownership,
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
    """
    Fetch NT stats for a player. Tries WC 2026 first (empty pre-tournament),
    then WC qualifying seasons (2024/2025) for each major confederation.
    API-Football league IDs for international competitions:
      WC 2026=1, UEFA NL=5, WC Qual EU=960, WC Qual SA=29, WC Qual CAF=29,
      WC Qual AFC=30, WC Qual CONCACAF=31, WC Qual OFC=32
    """
    intl_leagues = [WC_2026_LEAGUE_ID, 5, 960, 961, 29, 30, 31, 32]
    for season in [2026, 2025, 2024]:
        for league in intl_leagues:
            data = _api_football_get("players", {
                "id": player_id,
                "season": season,
                "league": league,
            })
            stats = _parse_stats(data) if data else None
            if stats and stats.matches > 0:
                return stats
    return None


def fetch_stats_club(player_id: int) -> Optional[PlayerStats]:
    data = _api_football_get("players", {
        "id": player_id,
        "season": CLUB_SEASON,
    })
    return _parse_stats(data) if data else None


# ── Per-90 blending ───────────────────────────────────────────────────────────

def _per90(val: float, minutes: int) -> float:
    return (val / minutes * 90) if minutes >= 45 else 0.0


def _compute_per90(p: Player) -> None:
    """Blend NT (65%) and club (35%) per-90 stats. Flip weights if NT < 5 apps."""
    nt = p.national_stats
    cl = p.club_stats

    nt_mins = nt.minutes if nt.minutes > 0 else nt.matches * 75
    cl_mins = cl.minutes if cl.minutes > 0 else cl.matches * 80

    nt_xg  = _per90(nt.goals,           nt_mins)
    nt_xa  = _per90(nt.assists,          nt_mins)
    nt_sot = _per90(nt.shots_on_target,  nt_mins)
    nt_kp  = _per90(nt.chances_created,  nt_mins)
    nt_tk  = _per90(nt.tackles,          nt_mins)

    cl_xg  = _per90(cl.goals,           cl_mins)
    cl_xa  = _per90(cl.assists,          cl_mins)
    cl_sot = _per90(cl.shots_on_target,  cl_mins)
    cl_kp  = _per90(cl.chances_created,  cl_mins)
    cl_tk  = _per90(cl.tackles,          cl_mins)

    # Override club stats from FBref/manual data (xG/kp90/tackles90 not in API raw counts).
    fbref = (_FBREF_BY_ID.get(p.id)
             or _FBREF_BY_NAME.get(_norm_name(p.name))
             or _FBREF_BY_NAME.get(_match_key(p.name)))
    if fbref:
        # stats.json stores actual goals as "goals90"; legacy manual files also
        # carry "xg90". Prefer real goals/90, fall back to xG/90 for legacy entries.
        _cl_goals = fbref.get("goals90") or fbref.get("xg90") or 0.0
        if _cl_goals > 0: cl_xg = _cl_goals
        if fbref.get("xa90",     0.0) > 0: cl_xa  = fbref["xa90"]
        if fbref.get("sot90",    0.0) > 0: cl_sot = fbref["sot90"]
        if fbref.get("kp90",     0.0) > 0: cl_kp  = fbref["kp90"]
        if fbref.get("tackles90",0.0) > 0: cl_tk  = fbref["tackles90"]
        if p.club_stats.matches == 0 and fbref.get("mp", 0) > 0:
            p.club_stats.matches = fbref["mp"]
        sr = fbref.get("starter_rate", 0.0)
        if sr > 0:
            p.starter_rate = sr
        # Backfill raw season totals from per-90 × minutes (stats.json is per-90 based,
        # so the count columns would otherwise show 0).
        cmin = fbref.get("minutes", 0) or 0
        if cmin > 0:
            p.club_stats.minutes         = cmin
            p.club_stats.goals           = round(cl_xg  * cmin / 90)
            p.club_stats.assists         = round(cl_xa  * cmin / 90)
            p.club_stats.shots_on_target = round(cl_sot * cmin / 90)
            p.club_stats.chances_created = round(cl_kp  * cmin / 90)
            p.club_stats.tackles         = round(cl_tk  * cmin / 90)

    # Override NT stats from manual_nt_stats.json when available.
    nt_manual = _NT_BY_NAME.get(_norm_name(p.name)) or _NT_BY_NAME.get(_match_key(p.name))
    if nt_manual:
        _nt_goals = nt_manual.get("goals90") or nt_manual.get("xg90") or 0.0
        if _nt_goals > 0 or nt_manual.get("mp", 0) >= 5:
            if _nt_goals > 0:           nt_xg = _nt_goals
            nt_xa  = nt_manual.get("xa90",  nt_xa)
            nt_sot = nt_manual.get("sot90", nt_sot)
            nt_kp  = nt_manual.get("kp90",  nt_kp)
            nt_tk  = nt_manual.get("tackles90", nt_tk)
        # Ensure nt.matches reflects real NT experience so nt_weight logic fires
        if p.national_stats.matches == 0 and nt_manual.get("mp", 0) > 0:
            p.national_stats.matches = nt_manual["mp"]
        if nt_manual.get("starter_rate", 0.0) > 0 and p.starter_rate == 1.0:
            p.starter_rate = nt_manual["starter_rate"]
        # Backfill raw NT totals from per-90 × minutes for the count columns.
        nmin = nt_manual.get("minutes", 0) or 0
        if nmin > 0:
            p.national_stats.minutes         = nmin
            p.national_stats.goals           = round(nt_xg  * nmin / 90)
            p.national_stats.assists         = round(nt_xa  * nmin / 90)
            p.national_stats.shots_on_target = round(nt_sot * nmin / 90)
            p.national_stats.chances_created = round(nt_kp  * nmin / 90)
            p.national_stats.tackles         = round(nt_tk  * nmin / 90)

    # Position-based display defaults for KP/tackles — shown in table but
    # NOT used in scoring so they don't inflate projected points for
    # players we have no real data on.
    _DEF_KP = {"GK": 0.2, "DEF": 0.6, "MID": 1.8, "FWD": 0.8}
    _DEF_TK = {"GK": 0.1, "DEF": 1.8, "MID": 2.0, "FWD": 0.5}
    pos = p.position

    nt_w, cl_w = (0.65, 0.35) if p.national_stats.matches >= 5 else (0.35, 0.65)

    # Club split — display uses position default when no real data
    p.xg90_club      = cl_xg
    p.xa90_club      = cl_xa
    p.sot90_club     = cl_sot
    p.kp90_club      = cl_kp if cl_kp > 0 else _DEF_KP.get(pos, 1.0)
    p.tackles90_club = cl_tk if cl_tk > 0 else _DEF_TK.get(pos, 1.0)

    # NT split — same
    p.xg90_nt      = nt_xg
    p.xa90_nt      = nt_xa
    p.sot90_nt     = nt_sot
    p.kp90_nt      = nt_kp if nt_kp > 0 else _DEF_KP.get(pos, 1.0)
    p.tackles90_nt = nt_tk if nt_tk > 0 else _DEF_TK.get(pos, 1.0)

    # Blended
    p.xg90      = nt_w * nt_xg  + cl_w * cl_xg
    p.xa90      = nt_w * nt_xa  + cl_w * cl_xa
    p.sot90     = nt_w * nt_sot + cl_w * cl_sot
    p.kp90      = nt_w * nt_kp  + cl_w * cl_kp
    p.tackles90 = nt_w * nt_tk  + cl_w * cl_tk

    # Effective sample size behind the blend — used to regress the per-90 "share"
    # multiplier toward the positional baseline for low-minute players (small
    # NT samples otherwise produce spiky, over-confident projections).
    eff_nt_min = p.national_stats.minutes if p.national_stats.minutes > 0 else nt_mins
    eff_cl_min = p.club_stats.minutes     if p.club_stats.minutes > 0     else cl_mins
    p._sample_minutes = nt_w * eff_nt_min + cl_w * eff_cl_min

    if p.position == "GK":
        shots_faced = nt.saves + nt.goals_conceded
        p.save_rate = (nt.saves / shots_faced) if shots_faced > 0 else 0.7


# ── Projection formula ────────────────────────────────────────────────────────

# Fraction of team xG/xA credited to each position type (sums to ~1.0)
_POS_XG_FRAC = {"GK": 0.02, "DEF": 0.12, "MID": 0.28, "FWD": 0.58}
_POS_XA_FRAC = {"GK": 0.01, "DEF": 0.20, "MID": 0.50, "FWD": 0.29}
# Typical starters per position in a XI
_N_STARTERS  = {"GK": 1,    "DEF": 4,    "MID": 4,    "FWD": 3}

# Default xg90 / xa90 per position when no data
_DEFAULT_XG90 = {"GK": 0.01, "DEF": 0.04, "MID": 0.10, "FWD": 0.35}
_DEFAULT_XA90 = {"GK": 0.01, "DEF": 0.05, "MID": 0.15, "FWD": 0.12}

# Share-multiplier guards: cap runaway ratios and shrink toward the positional
# baseline (1.0) for small samples. w = mins / (mins + SHARE_K); at SHARE_K
# minutes a player gets half-weight on their measured edge over the average.
SHARE_CAP = 3.0
SHARE_K   = 500.0


def _shrunk_share(p90: float, avg: float, sample_min: float) -> float:
    """Sample-size-regressed, capped ratio of a player's per-90 to the pos average."""
    if avg <= 0 or p90 <= 0:
        return 1.0
    raw = p90 / avg
    w = sample_min / (sample_min + SHARE_K)
    share = 1.0 + w * (raw - 1.0)
    return min(share, SHARE_CAP)


def _pos_averages(players: list) -> tuple:
    xg_by_pos: dict = {p: [] for p in ["GK", "DEF", "MID", "FWD"]}
    xa_by_pos: dict = {p: [] for p in ["GK", "DEF", "MID", "FWD"]}
    for p in players:
        if p.xg90 > 0:
            xg_by_pos[p.position].append(p.xg90)
        if p.xa90 > 0:
            xa_by_pos[p.position].append(p.xa90)
    avg_xg = {pos: (sum(v) / len(v) if v else _DEFAULT_XG90[pos]) for pos, v in xg_by_pos.items()}
    avg_xa = {pos: (sum(v) / len(v) if v else _DEFAULT_XA90[pos]) for pos, v in xa_by_pos.items()}
    return avg_xg, avg_xa


def _player_xg(p: Player, team_xg: float, avg_xg: dict) -> float:
    """Individual expected goals for one matchday."""
    pos = p.position
    base = team_xg * _POS_XG_FRAC[pos] / _N_STARTERS[pos]
    share = _shrunk_share(p.xg90, avg_xg[pos], getattr(p, "_sample_minutes", 0.0))
    return base * share


def _player_xa(p: Player, team_xg: float, avg_xa: dict) -> float:
    """Individual expected assists for one matchday."""
    pos = p.position
    base = (team_xg * 0.75) * _POS_XA_FRAC[pos] / _N_STARTERS[pos]
    share = _shrunk_share(p.xa90, avg_xa[pos], getattr(p, "_sample_minutes", 0.0))
    return base * share


def _project_md(p: Player, md: int, avg_xg: dict, avg_xa: dict) -> tuple:
    """Project points for one matchday, scaled by projected minutes.
    Returns (pts, player_xg-for-the-minutes-played)."""
    pos = p.position
    team_xg, cs_pct = get_team_proj(p.team_code, md)
    opp_xg = get_opponent_xg(p.team_code, md)

    # Minutes scaling: returns accrue per minute on the pitch; clean sheets need
    # 60+ minutes; appearance is 2 pts for 60+ min, else 1 pt.
    mins = getattr(p, "projected_minutes", 90.0)
    mf = mins / 90.0

    pxg = _player_xg(p, team_xg, avg_xg) * mf
    pxa = _player_xa(p, team_xg, avg_xa) * mf

    # Set-piece duty bonuses — penalties/direct free kicks add xG, corners add xA.
    # Flat per-game expectations, minutes-scaled like everything else.
    pxg += (p.sp_pk_xg + p.sp_fk_xg) * mf
    pxa += p.sp_ck_xa * mf

    pts = 2.0 if mins >= 60 else 1.0       # appearance points
    pts += pxg * SCORING["goal"][pos]
    pts += pxa * 3
    if mins >= 60:
        pts += cs_pct * SCORING["clean_sheet_60"][pos]

    if pos in ("GK", "DEF"):
        pts += max(0.0, opp_xg - 1.0) * SCORING["goals_conceded_add"][pos] * mf

    if pos == "GK":
        pts += (opp_xg * 3.5 * p.save_rate) / 3 * mf

    if pos == "MID":
        pts += (p.tackles90 / 3 + p.kp90 / 2) * mf

    if pos == "FWD":
        pts += p.sot90 / 2 * mf

    return max(0.0, pts), pxg


def _assign_minutes(players: list) -> None:
    """
    Set projected_minutes for every player.
      - Team has a predicted XI (data/predicted_lineups.py):
          in XI  -> STARTER_MINUTES (70),  not in XI -> BENCH_MINUTES (20)
      - Team has no predicted XI: fall back to starter_rate from the stats
        pipeline, mapped onto [BENCH, STARTER]  (sr 0 -> 20, sr 1 -> ~70).
    """
    xi_keys: dict[str, set] = {
        code: {_match_key(n) for n in names} for code, names in PREDICTED_XI.items()
    }
    for p in players:
        keys = xi_keys.get(p.team_code)
        if keys is not None:
            if _match_key(p.name) in keys:
                p.projected_minutes = float(STARTER_MINUTES)
                p.predicted_starter = True
            else:
                p.projected_minutes = float(BENCH_MINUTES)
                p.predicted_starter = False
        else:
            # No XI for this team — use starter_rate as a soft minutes estimate
            sr = max(0.0, min(1.0, p.starter_rate if p.starter_rate is not None else 1.0))
            p.projected_minutes = round(BENCH_MINUTES + sr * (STARTER_MINUTES - BENCH_MINUTES))
            p.predicted_starter = sr >= 0.6


# ── Set-piece duty assignment ─────────────────────────────────────────────────

# Per-game expected value of each duty (before pos-weighting / minutes scaling).
#   PK: ~0.18 pens awarded per team-game × ~0.78 conversion ≈ 0.14 xG
#   FK: direct free-kick goals are rare ≈ 0.04 xG
#   CK: a designated corner taker sources extra set-piece assists ≈ 0.06 xA
_PK_XG = 0.14
_FK_XG = 0.04
_CK_XA = 0.06
# Primary/secondary split when a duty is shared between two listed names.
_DUTY_WEIGHTS = {1: [1.0], 2: [0.65, 0.35]}


def _name_tokens(name: str) -> list:
    """Tokenise a name for set-piece matching: accent-strip, drop dots/hyphens."""
    s = _norm_name(name).replace(".", " ").replace("-", " ").replace("'", " ")
    return [t for t in s.split() if t]


def _taker_matches(player_name: str, spec: str) -> bool:
    """True if a squad player matches a set-piece taker fragment.

    Surname tokens (len>=2) must all appear as whole tokens in the player's name;
    single-letter initials must prefix some player token (disambiguates e.g.
    'L. Bacuna' vs 'J. Bacuna')."""
    p_toks = _name_tokens(player_name)
    s_toks = _name_tokens(spec)
    surnames = [t for t in s_toks if len(t) >= 2]
    initials = [t for t in s_toks if len(t) == 1]
    if not surnames or not all(t in p_toks for t in surnames):
        return False
    return all(any(tok.startswith(ini) for tok in p_toks) for ini in initials)


def _assign_set_pieces(players: list) -> None:
    """Flag set-piece takers and store their per-90 xG/xA duty bonuses."""
    by_team: dict[str, list] = {}
    for p in players:
        by_team.setdefault(p.team_code, []).append(p)

    for code, roster in by_team.items():
        spec = SET_PIECES.get(code)
        if not spec:
            continue
        for role, takers in spec.items():
            weights = _DUTY_WEIGHTS.get(len(takers), [1.0] * len(takers))
            for taker, w in zip(takers, weights):
                for p in roster:
                    if not _taker_matches(p.name, taker):
                        continue
                    if role == "PK":
                        p.sp_pk_xg = max(p.sp_pk_xg, w * _PK_XG)
                    elif role == "FK":
                        p.sp_fk_xg = max(p.sp_fk_xg, w * _FK_XG)
                    elif role == "CK":
                        p.sp_ck_xa = max(p.sp_ck_xa, w * _CK_XA)
                    break  # first matching player per taker fragment

    for p in players:
        roles = []
        if p.sp_pk_xg > 0: roles.append("PK")
        if p.sp_fk_xg > 0: roles.append("FK")
        if p.sp_ck_xa > 0: roles.append("CK")
        p.sp_roles = "·".join(roles)


def build_projections(players: list, matchdays: list = None) -> pd.DataFrame:
    """
    Compute per-90 blended stats, then project points for given matchdays.
    Default: GD1 + GD2 cumulative.
    """
    if matchdays is None:
        matchdays = [1, 2]

    for p in players:
        _compute_per90(p)

    _assign_minutes(players)     # needs starter_rate set by _compute_per90
    _assign_set_pieces(players)  # flag PK/FK/CK takers from data/set_pieces.py

    avg_xg, avg_xa = _pos_averages(players)

    for p in players:
        results = [_project_md(p, md, avg_xg, avg_xa) for md in matchdays]
        md_pts  = [r[0] for r in results]
        md_pxg  = [r[1] for r in results]
        p.xpts_per_match   = round(sum(md_pts) / len(md_pts), 3)
        p.xpts_group_stage = round(sum(md_pts), 2)
        p._xg_by_md  = md_pxg   # player-level xG per matchday
        p._pts_by_md = md_pts   # projected points per matchday
        if p.price > 0:
            p.value = round(p.xpts_group_stage / p.price, 3)
        p.scout_flag = p.xpts_per_match > SCOUT_POINTS_THRESHOLD and p.is_differential

    return _to_dataframe(players, matchdays)


def _to_dataframe(players: list, matchdays: list = None) -> pd.DataFrame:
    if matchdays is None:
        matchdays = [1, 2]
    rows = []
    for p in players:
        fdr_total = get_team_fdr_total(p.team_code)
        avg_cs = get_avg_cs_pct(p.team_code)
        avg_goals = get_avg_proj_goals(p.team_code)
        cs_vals = CS_PCT.get(p.team_code, ["-", "-", "-"])
        g_vals = PROJ_GOALS.get(p.team_code, ["-", "-", "-"])
        fdr_vals = FDR.get(p.team_code, ["-", "-", "-"])

        xg_by_md  = getattr(p, "_xg_by_md",  [0.0] * len(matchdays))
        pts_by_md = getattr(p, "_pts_by_md", [0.0] * len(matchdays))
        xg_gd1  = round(xg_by_md[0],  3) if len(xg_by_md)  > 0 else 0.0
        xg_gd2  = round(xg_by_md[1],  3) if len(xg_by_md)  > 1 else 0.0
        md1_pts = round(pts_by_md[0],  1) if len(pts_by_md) > 0 else 0.0
        md2_pts = round(pts_by_md[1],  1) if len(pts_by_md) > 1 else 0.0

        # Fixture opponents (for display)
        team_fix    = FIXTURES.get(p.team_code, [])
        md1_opp_raw = team_fix[0] if len(team_fix) > 0 else ""
        md2_opp_raw = team_fix[1] if len(team_fix) > 1 else ""
        md1_opp = md1_opp_raw or "?"
        md2_opp = md2_opp_raw or "?"

        # Raw CS% floats (separate from the formatted cs_md1/cs_md2 strings)
        raw_cs = CS_PCT.get(p.team_code, [0.3, 0.3, 0.3])
        cs_md1_pct = raw_cs[0] if len(raw_cs) > 0 else 0.3
        cs_md2_pct = raw_cs[1] if len(raw_cs) > 1 else 0.3

        rows.append({
            "id": p.id,
            "name": p.name,
            "pos": p.position,
            "country": p.team_name,
            "team_code": p.team_code,
            "club": p.club,
            "price": p.price,
            "own_%": round(p.ownership_pct, 1),
            "set_pieces": p.sp_roles,
            "xPts/game": p.xpts_per_match,
            "xPts_GS": p.xpts_group_stage,
            "value": p.value,
            "scout": p.scout_flag,
            # Spec display columns
            "GD1 xG": xg_gd1,
            "GD2 xG": xg_gd2,
            "md1_opp":    md1_opp,
            "md2_opp":    md2_opp,
            "cs_md1_pct": cs_md1_pct,
            "cs_md2_pct": cs_md2_pct,
            "md1_pts":    md1_pts,
            "md2_pts":    md2_pts,
            "goals/90": round(p.xg90, 3),
            "assists/90": round(p.xa90, 3),
            "xg90_club": round(p.xg90_club, 3),
            "xa90_club": round(p.xa90_club, 3),
            "sot90_club": round(p.sot90_club, 3),
            "kp90_club": round(p.kp90_club, 3),
            "tackles90_club": round(p.tackles90_club, 3),
            "xg90_nt": round(p.xg90_nt, 3),
            "xa90_nt": round(p.xa90_nt, 3),
            "sot90_nt": round(p.sot90_nt, 3),
            "kp90_nt": round(p.kp90_nt, 3),
            "tackles90_nt": round(p.tackles90_nt, 3),
            "nt_weight":    "65% NT" if p.national_stats.matches >= 5 else "35% NT",
            "starter_rate": round(p.starter_rate, 2),
            "proj_min":     int(round(p.projected_minutes)),
            "predicted_starter": p.predicted_starter,
            # Raw stats for expander
            "intl_games": p.national_stats.matches,
            "intl_minutes": p.national_stats.minutes,
            "intl_goals": p.national_stats.goals,
            "intl_assists": p.national_stats.assists,
            "intl_cs": p.national_stats.clean_sheets,
            "intl_sot": round(p.national_stats.shots_on_target, 1),
            "intl_chances": round(p.national_stats.chances_created, 1),
            "intl_tackles": round(p.national_stats.tackles, 1),
            "intl_saves": round(p.national_stats.saves, 1),
            "club_games": p.club_stats.matches,
            "club_minutes": p.club_stats.minutes,
            "club_goals": p.club_stats.goals,
            "club_assists": p.club_stats.assists,
            "club_cs": p.club_stats.clean_sheets,
            "club_sot": round(p.club_stats.shots_on_target, 1),
            "club_chances": round(p.club_stats.chances_created, 1),
            "club_tackles": round(p.club_stats.tackles, 1),
            "club_saves": round(p.club_stats.saves, 1),
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
FIFA_FEED_FILE = "data/fifa_players.json"  # offline snapshot of the real FIFA Fantasy roster

# Default price estimates by position (used when FIFA Fantasy prices not available)
_DEFAULT_PRICE = {"GK": 5.0, "DEF": 5.5, "MID": 7.0, "FWD": 8.0}


def _build_club_lookup() -> dict:
    """match_key(name) -> club, from wc_squads.json (display only — feed has no club)."""
    m: dict[str, str] = {}
    if not os.path.exists(WC_SQUADS_FILE):
        return m
    try:
        data = json.load(open(WC_SQUADS_FILE))
    except Exception:
        return m
    for _, td in data.get("teams", {}).items():
        for p in td.get("players", []):
            club = p.get("club", "")
            if club:
                m.setdefault(_match_key(p.get("name", "")), club)
    return m


def load_from_fifa_feed() -> list:
    """
    Build the player pool from the real FIFA Fantasy feed (data/fifa_players.json).
    This is the authoritative roster: only players actually in the game, with real
    FIFA IDs, names, prices, and ownership. Per-90 stats are matched separately by
    name in _compute_per90. Club names come from wc_squads (feed omits them).
    """
    if not os.path.exists(FIFA_FEED_FILE):
        return []
    try:
        feed = json.load(open(FIFA_FEED_FILE))
    except Exception as e:
        print(f"[FIFA feed] Could not load {FIFA_FEED_FILE}: {e}")
        return []

    club_lookup = _build_club_lookup()
    players, seen = [], set()
    skipped_squad = 0
    for e in feed:
        if e.get("status") == "transferred":
            continue
        code = FIFA_TEAM_ID_TO_CODE.get(e.get("squadId"))
        if not code or code not in TEAM_NAMES:
            skipped_squad += 1
            continue
        name = e.get("knownName") or f"{e.get('firstName','')} {e.get('lastName','')}".strip()
        if not name:
            continue
        pid = str(e.get("id"))
        if pid in seen:
            continue
        seen.add(pid)
        pos = POSITION_MAP.get(e.get("position"), "MID")
        players.append(Player(
            id=pid,
            name=name,
            position=pos,
            team_code=code,
            club=club_lookup.get(_match_key(name), ""),
            price=float(e.get("price") or _DEFAULT_PRICE.get(pos, 6.0)),
            ownership_pct=float(e.get("percentSelected") or 0.0),
        ))
    print(f"[FIFA feed] Loaded {len(players)} players "
          f"({skipped_squad} skipped: unmapped squad / non-WC)")
    return players


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

            price = float(p.get("price") or _DEFAULT_PRICE.get(pos, 6.0))
            own   = float(p.get("ownership_pct") or p.get("ownership") or 0.0)

            players.append(Player(
                id=pid,
                name=p.get("name", "Unknown"),
                position=pos,
                team_code=team_code,
                club=p.get("club", ""),
                price=price,
                ownership_pct=own,
                national_stats=nat_stats,
            ))
    return players


PLAYER_SOURCE: str = "unknown"  # 'api', 'squads', 'squads_fallback', 'local', 'demo'


def load_data(
    session_token: Optional[str] = None,
    players_file: Optional[str] = None,
    use_demo: bool = False,
    use_squads: bool = False,
    enrich_with_api: bool = True,
) -> pd.DataFrame:
    """Main entry point. Fetches players + stats, returns ranked DataFrame."""
    global PLAYER_SOURCE

    if use_demo:
        PLAYER_SOURCE = "demo"
        players = get_demo_players()
    elif use_squads:
        # Prefer the real FIFA feed (authoritative roster + real prices/ownership);
        # fall back to the older wc_squads.json, then demo.
        players = load_from_fifa_feed()
        if players:
            PLAYER_SOURCE = "fifa_feed"
        else:
            PLAYER_SOURCE = "squads"
            players = load_from_wc_squads() or get_demo_players()
    elif players_file:
        PLAYER_SOURCE = "local"
        players = load_players_from_json(players_file)
    else:
        # Always try the live FIFA Fantasy API first
        players = fetch_fantasy_players(session_token)
        if players:
            PLAYER_SOURCE = "api"
        else:
            # API unreachable — fall back to static squad data
            PLAYER_SOURCE = "squads_fallback"
            players = load_from_wc_squads()
        if not players:
            PLAYER_SOURCE = "demo"
            players = get_demo_players()

    return build_projections(players)
