"""
Fetches player statistics from API-Football (api-sports.io).
Handles WC 2026 national team stats and recent club stats separately.
Results are cached to disk to avoid burning rate-limit quota.
"""

import json
import os
import time
import requests
from typing import Optional

from config import API_FOOTBALL_KEY, API_FOOTBALL_BASE, CACHE_DIR, WC_2026_LEAGUE_ID, WC_2026_SEASON
from src.api.models import PlayerStats


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cache(key: str) -> Optional[dict]:
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_cache(key: str, data: dict) -> None:
    with open(_cache_path(key), "w") as f:
        json.dump(data, f, indent=2)


def _get(endpoint: str, params: dict) -> Optional[dict]:
    """Make an authenticated GET request to API-Football with caching."""
    cache_key = endpoint.replace("/", "_") + "_" + "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    cached = _load_cache(cache_key)
    if cached:
        return cached

    if not API_FOOTBALL_KEY:
        raise ValueError(
            "API_FOOTBALL_KEY not set. Get a free key at https://dashboard.api-football.com/ "
            "and add it to your .env file."
        )

    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    url = f"{API_FOOTBALL_BASE}/{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    _save_cache(cache_key, data)
    time.sleep(0.3)  # be polite to rate limits
    return data


def get_wc_squads() -> list[dict]:
    """Get all squads registered for WC 2026."""
    data = _get("players/squads", {"league": WC_2026_LEAGUE_ID, "season": WC_2026_SEASON})
    return data.get("response", [])


def get_player_stats_national(player_id: int, team_id: int) -> Optional[PlayerStats]:
    """Fetch national team stats for a player in WC 2026 / qualifiers."""
    data = _get("players", {
        "id": player_id,
        "season": WC_2026_SEASON,
        "league": WC_2026_LEAGUE_ID,
    })
    return _parse_player_stats(data, team_id)


def get_player_stats_club(player_id: int, club_id: int, season: int = 2024) -> Optional[PlayerStats]:
    """Fetch club stats for a player in their domestic league (recent season)."""
    data = _get("players", {
        "id": player_id,
        "season": season,
    })
    return _parse_player_stats(data, club_id)


def _parse_player_stats(data: dict, team_id: int) -> Optional[PlayerStats]:
    """Parse API-Football response into a PlayerStats object."""
    responses = data.get("response", [])
    if not responses:
        return None

    player_data = responses[0]
    stats_list = player_data.get("statistics", [])

    # Find stats for the specific team
    team_stats = None
    for s in stats_list:
        if s.get("team", {}).get("id") == team_id:
            team_stats = s
            break

    if not team_stats and stats_list:
        # Fall back to first available stats
        team_stats = stats_list[0]

    if not team_stats:
        return None

    games = team_stats.get("games", {})
    goals = team_stats.get("goals", {})
    shots = team_stats.get("shots", {})
    passes = team_stats.get("passes", {})
    tackles = team_stats.get("tackles", {})
    duels = team_stats.get("duels", {})
    cards = team_stats.get("cards", {})
    penalty = team_stats.get("penalty", {})

    matches = games.get("appearences") or 0  # note: API typo "appearences"
    minutes = games.get("minutes") or 0

    return PlayerStats(
        matches=matches,
        minutes=minutes,
        goals=goals.get("total") or 0,
        assists=goals.get("assists") or 0,
        shots_on_target=shots.get("on") or 0,
        chances_created=passes.get("key") or 0,        # key passes ≈ chances created
        tackles=tackles.get("total") or 0,
        clean_sheets=games.get("lineups") or 0,        # will be refined from fixture data
        saves=games.get("saves") or 0,
        yellow_cards=cards.get("yellow") or 0,
        red_cards=cards.get("red") or 0,
        goals_conceded=goals.get("conceded") or 0,
        penalties_saved=penalty.get("saved") or 0,
        penalties_missed=penalty.get("missed") or 0,
    )


def get_fixtures(league_id: int, season: int, team_id: int) -> list[dict]:
    """Get all fixtures for a team in a given league/season."""
    data = _get("fixtures", {
        "league": league_id,
        "season": season,
        "team": team_id,
        "status": "FT",
    })
    return data.get("response", [])


def get_clean_sheets_from_fixtures(league_id: int, season: int, team_id: int) -> int:
    """Count clean sheets from fixture results for a team."""
    fixtures = get_fixtures(league_id, season, team_id)
    clean_sheets = 0
    for f in fixtures:
        goals = f.get("goals", {})
        teams = f.get("teams", {})
        home_team_id = teams.get("home", {}).get("id")
        is_home = home_team_id == team_id
        if is_home:
            conceded = goals.get("away", 0) or 0
        else:
            conceded = goals.get("home", 0) or 0
        if conceded == 0:
            clean_sheets += 1
    return clean_sheets


def search_player(name: str) -> list[dict]:
    """Search for a player by name."""
    data = _get("players", {"search": name, "season": WC_2026_SEASON})
    return data.get("response", [])


def get_all_teams_wc2026() -> list[dict]:
    """Get all teams in WC 2026."""
    data = _get("teams", {"league": WC_2026_LEAGUE_ID, "season": WC_2026_SEASON})
    return data.get("response", [])
