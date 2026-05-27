"""
Fetches player data from the official FIFA World Cup Fantasy game.
Endpoint: https://play.fifa.com/json/fantasy/

The official game uses session-based auth. We support two modes:
1. With a session token (most accurate ownership + prices)
2. Without token — falls back to cached/static player list if available
"""

import json
import os
import time
import requests
from typing import Optional

from config import CACHE_DIR
from src.api.models import Player, PlayerStats

FIFA_FANTASY_BASE = "https://play.fifa.com/json/fantasy"

POSITION_MAP = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD",
    # alternate encodings
    "GK": "GK",
    "DEF": "DEF",
    "MID": "MID",
    "FWD": "FWD",
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Forward": "FWD",
    "Attacker": "FWD",
}


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cache(key: str) -> Optional[dict]:
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_cache(key: str, data) -> None:
    with open(_cache_path(key), "w") as f:
        json.dump(data, f, indent=2)


def fetch_players(session_token: Optional[str] = None) -> list[Player]:
    """
    Fetch all players from the FIFA Fantasy API.
    Returns a list of Player objects with price and ownership populated.

    session_token: Optional Bearer token from play.fifa.com (copy from browser DevTools
                   → Network → any /json/fantasy/ request → Authorization header).
                   If omitted, uses cached data if available.
    """
    cached = _load_cache("fifa_fantasy_players")
    if cached and not session_token:
        return _parse_players(cached)

    headers = {"Accept": "application/json"}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"

    try:
        resp = requests.get(
            f"{FIFA_FANTASY_BASE}/players",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        _save_cache("fifa_fantasy_players", data)
        return _parse_players(data)
    except requests.HTTPError as e:
        if cached:
            print(f"[fifa_fantasy] Live fetch failed ({e}), using cached data.")
            return _parse_players(cached)
        raise RuntimeError(
            f"Cannot fetch FIFA Fantasy players: {e}\n"
            "Provide a session token (see README) or ensure cached data exists."
        )


def _parse_players(data) -> list[Player]:
    """Parse the FIFA Fantasy API response into Player objects."""
    players = []

    # Handle different possible response shapes
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = (
            data.get("players")
            or data.get("data")
            or data.get("response")
            or []
        )
    else:
        return []

    for raw in raw_list:
        pos_raw = raw.get("position") or raw.get("positionId") or raw.get("pos") or "MID"
        position = POSITION_MAP.get(pos_raw, POSITION_MAP.get(str(pos_raw), "MID"))

        player = Player(
            id=str(raw.get("id") or raw.get("playerId") or ""),
            name=raw.get("name") or raw.get("playerName") or raw.get("knownName") or "",
            position=position,
            team_country=(
                raw.get("teamName")
                or raw.get("countryName")
                or raw.get("teamCode")
                or ""
            ),
            team_country_id=raw.get("teamId") or raw.get("countryId"),
            club=raw.get("clubName") or raw.get("club") or "",
            club_id=raw.get("clubId"),
            price=_parse_price(raw),
            ownership_pct=float(
                raw.get("ownership")
                or raw.get("ownershipPercent")
                or raw.get("selectedBy")
                or 0.0
            ),
        )
        players.append(player)

    return players


def _parse_price(raw: dict) -> float:
    """Extract price in millions from various possible fields."""
    for field in ("price", "cost", "value", "buyPrice"):
        val = raw.get(field)
        if val is not None:
            val = float(val)
            # API returns price in different units — normalize to millions
            if val > 200:   # likely in 100k units (e.g., 85 = $8.5m)
                return val / 10
            return val
    return 0.0


def load_players_from_file(path: str) -> list[Player]:
    """Load players from a local JSON file (manual export from browser)."""
    with open(path) as f:
        data = json.load(f)
    return _parse_players(data)


def save_players_to_cache(players: list[Player]) -> None:
    """Persist player list back to cache as raw dict list."""
    raw = []
    for p in players:
        raw.append({
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "teamName": p.team_country,
            "teamId": p.team_country_id,
            "clubName": p.club,
            "clubId": p.club_id,
            "price": p.price,
            "ownership": p.ownership_pct,
        })
    _save_cache("fifa_fantasy_players", raw)
