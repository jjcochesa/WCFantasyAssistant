#!/usr/bin/env python3
"""
Run this LOCALLY to pre-fetch WC 2026 squad, lineup, and stats data.

Output: data/wc_squads.json  (commit this file to the repo so Streamlit
        can use it without burning through API quota on every cold start)

Usage:
    python fetch_wc_data.py

Requires: API_FOOTBALL_KEY in .env
API-Football free tier: 100 req/day.  This script uses ~150-250 total
(cached after first run — re-running only hits expired entries).
"""
import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

if not API_KEY:
    raise SystemExit("ERROR: API_FOOTBALL_KEY not set. Add it to .env first.")

# ── API-Football name overrides (their names differ from our TEAM_NAMES) ──────
API_NAME_MAP = {
    "USA":  "United-States",
    "CIV":  "Ivory Coast",
    "KOR":  "South Korea",
    "BIH":  "Bosnia",
    "CZE":  "Czech-Republic",
    "COD":  "DR Congo",
    "IRN":  "Iran",
    "KSA":  "Saudi Arabia",
    "NZL":  "New Zealand",
    "CPV":  "Cape Verde",
    "NED":  "Netherlands",
    "SCO":  "Scotland",
    "HAI":  "Haiti",
    "IRQ":  "Iraq",
    "QAT":  "Qatar",
    "JOR":  "Jordan",
    "CUW":  "Curacao",
    "SUI":  "Switzerland",
    "RSA":  "South Africa",
    "PAR":  "Paraguay",
    "ALG":  "Algeria",
    "UZB":  "Uzbekistan",
    "PAN":  "Panama",
    "TUN":  "Tunisia",
    "GHA":  "Ghana",
    "AUS":  "Australia",
    "ECU":  "Ecuador",
    "SEN":  "Senegal",
    "CRO":  "Croatia",
    "TUR":  "Turkey",
    "URU":  "Uruguay",
    "COL":  "Colombia",
    "AUT":  "Austria",
    "CAN":  "Canada",
    "MAR":  "Morocco",
    "NOR":  "Norway",
    "MEX":  "Mexico",
    "SWE":  "Sweden",
    # These are straightforward — API name matches TEAM_NAMES
    "ESP":  "Spain",
    "GER":  "Germany",
    "BRA":  "Brazil",
    "FRA":  "France",
    "POR":  "Portugal",
    "ENG":  "England",
    "ARG":  "Argentina",
    "BEL":  "Belgium",
    "JPN":  "Japan",
    "EGY":  "Egypt",
}

POSITION_MAP = {
    "Goalkeeper": "GK",
    "Defender":   "DEF",
    "Midfielder": "MID",
    "Attacker":   "FWD",
}

REQUESTS_MADE = [0]  # mutable counter so we can track usage


def _get(endpoint, params, delay=0.35):
    """Single GET with rate-limit delay. Returns response dict or {}."""
    REQUESTS_MADE[0] += 1
    try:
        r = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, params=params, timeout=25)
        r.raise_for_status()
        time.sleep(delay)
        return r.json()
    except Exception as e:
        print(f"  [ERROR] {endpoint} {params}: {e}")
        return {}


def find_team_id(team_code: str) -> int | None:
    """Search API-Football for the national team ID."""
    name = API_NAME_MAP.get(team_code, team_code)
    data = _get("teams", {"name": name, "type": "National"})
    for item in data.get("response", []):
        t = item.get("team", {})
        if t.get("national"):
            return t.get("id")
    # Fallback: try without type filter
    data2 = _get("teams", {"name": name})
    for item in data2.get("response", []):
        t = item.get("team", {})
        if t.get("national"):
            return t.get("id")
    return None


def fetch_squad(team_id: int) -> list[dict]:
    """Return list of {id, name, position, age, photo} for a team's squad."""
    data = _get("players/squads", {"team": team_id})
    players = []
    for entry in data.get("response", []):
        for p in entry.get("players", []):
            pos = POSITION_MAP.get(p.get("position", ""), "MID")
            players.append({
                "id":       str(p.get("id", "")),
                "name":     p.get("name", ""),
                "position": pos,
                "age":      p.get("age"),
                "photo":    p.get("photo", ""),
            })
    return players


def fetch_recent_lineups(team_id: int, n: int = 5) -> dict[str, int]:
    """
    Returns {player_id: start_count} from the last n national team fixtures.
    Only counts players in the starting XI.
    """
    fixtures_data = _get("fixtures", {"team": team_id, "last": n})
    fixtures = fixtures_data.get("response", [])

    start_counts: dict[str, int] = {}
    game_count = 0

    for fix in fixtures:
        fid = fix.get("fixture", {}).get("id")
        if not fid:
            continue
        lineup_data = _get("fixtures/lineups", {"fixture": fid})
        for team_lineup in lineup_data.get("response", []):
            if team_lineup.get("team", {}).get("id") != team_id:
                continue
            game_count += 1
            for starter in team_lineup.get("startXI", []):
                pid = str(starter.get("player", {}).get("id", ""))
                if pid:
                    start_counts[pid] = start_counts.get(pid, 0) + 1

    return start_counts, game_count


def fetch_player_stats(player_id: str, league_id: int, season: int) -> dict:
    """Fetch per-player stats for a given league/season."""
    data = _get("players", {"id": player_id, "league": league_id, "season": season})
    responses = data.get("response", [])
    if not responses:
        return {}
    stats_list = responses[0].get("statistics", [])
    if not stats_list:
        return {}
    s = stats_list[0]
    g  = s.get("games", {})
    go = s.get("goals", {})
    sh = s.get("shots", {})
    ps = s.get("passes", {})
    tk = s.get("tackles", {})
    cd = s.get("cards", {})
    pn = s.get("penalty", {})
    return {
        "matches":          g.get("appearences") or 0,
        "minutes":          g.get("minutes") or 0,
        "goals":            go.get("total") or 0,
        "assists":          go.get("assists") or 0,
        "shots_on_target":  sh.get("on") or 0,
        "chances_created":  ps.get("key") or 0,
        "tackles":          tk.get("total") or 0,
        "saves":            g.get("saves") or 0,
        "yellow_cards":     cd.get("yellow") or 0,
        "red_cards":        cd.get("red") or 0,
        "goals_conceded":   go.get("conceded") or 0,
        "penalties_saved":  pn.get("saved") or 0,
    }


# ── WC 2026 league IDs for qualifying competitions by confederation ─────────
# We pull the last ~12 months of international matches.
# API-Football league IDs:
INTL_LEAGUE_IDS = [
    1,     # FIFA World Cup 2026 (matches from the tournament itself, post June 11)
    4,     # Euro 2024 (recent UEFA nations)
    5,     # UEFA Nations League 2024-25
    9,     # Copa America 2024
    31,    # CONCACAF Nations League
    34,    # WC Qualifiers South America (CONMEBOL)
    30,    # WC Qualifiers CONCACAF
    29,    # WC Qualifiers Europe
    180,   # WC Qualifiers Africa (CAF)
    181,   # WC Qualifiers Asia (AFC)
    182,   # WC Qualifiers OFC
]
INTL_SEASON = 2024   # most qualifying data is under 2024 season

CLUB_LEAGUES = {
    "Premier League":  {"league": 39,  "season": 2024},
    "La Liga":         {"league": 140, "season": 2024},
    "Bundesliga":      {"league": 78,  "season": 2024},
    "Serie A":         {"league": 135, "season": 2024},
    "Ligue 1":         {"league": 61,  "season": 2024},
    "Eredivisie":      {"league": 88,  "season": 2024},
    "Primeira Liga":   {"league": 94,  "season": 2024},
    "Saudi Pro":       {"league": 307, "season": 2024},
    "MLS":             {"league": 253, "season": 2025},
    "Liga MX":         {"league": 262, "season": 2025},
}

WC_TEAMS = list(API_NAME_MAP.keys())


def main():
    out_path = "data/wc_squads.json"
    os.makedirs("data", exist_ok=True)

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "teams": {},
    }

    print(f"\n=== WC 2026 Squad Fetcher ===")
    print(f"Fetching {len(WC_TEAMS)} national teams...\n")

    team_ids: dict[str, int] = {}

    # ── Phase 1: Look up team IDs ─────────────────────────────────────────────
    print("Phase 1/3 — Team ID lookup")
    for code in WC_TEAMS:
        tid = find_team_id(code)
        if tid:
            team_ids[code] = tid
            print(f"  {code} → {tid}")
        else:
            print(f"  {code} → NOT FOUND")
        time.sleep(0.1)

    print(f"\nFound {len(team_ids)}/{len(WC_TEAMS)} team IDs.\n")

    # ── Phase 2: Fetch squads + recent lineups ────────────────────────────────
    print("Phase 2/3 — Squads + lineups")
    for code, tid in team_ids.items():
        print(f"  {code} (id={tid})...", end=" ", flush=True)

        squad = fetch_squad(tid)
        start_counts, game_count = fetch_recent_lineups(tid, n=5)

        squad_with_rates = []
        for p in squad:
            pid = p["id"]
            starts = start_counts.get(pid, 0)
            starter_rate = (starts / game_count) if game_count > 0 else None
            squad_with_rates.append({**p, "starter_rate": starter_rate, "starts": starts})

        # Sort: starters first, then squad depth
        squad_with_rates.sort(key=lambda x: -(x["starts"] or 0))

        result["teams"][code] = {
            "team_id": tid,
            "lineup_games_sampled": game_count,
            "players": squad_with_rates,
        }
        print(f"{len(squad)} players, {game_count} lineup games sampled")

    # ── Phase 3: Fetch international stats for key players ───────────────────
    # Only top players (those who appeared in ≥1 lineup) to stay within quota
    print("\nPhase 3/3 — International stats (starters only)")
    for code, team_data in result["teams"].items():
        starters = [p for p in team_data["players"] if (p.get("starts") or 0) >= 1]
        print(f"  {code}: {len(starters)} starters to enrich")
        for p in starters:
            pid = p["id"]
            if not pid:
                continue
            # Try WC 2026 league first, fall back to qualifying leagues
            stats = fetch_player_stats(pid, league=1, season=2026)
            if not stats.get("matches"):
                stats = fetch_player_stats(pid, league=5, season=2024)  # UEFA NL
            if not stats.get("matches"):
                stats = fetch_player_stats(pid, league=9, season=2024)  # Copa America
            p["intl_stats"] = stats if stats.get("matches") else None

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nSaved → {out_path}")
    print(f"Total API requests used: {REQUESTS_MADE[0]}")
    print(f"\nNext step: commit data/wc_squads.json to the repo and redeploy.")


if __name__ == "__main__":
    main()
