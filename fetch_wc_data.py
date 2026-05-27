#!/usr/bin/env python3
"""
Run this LOCALLY to pre-fetch WC 2026 squad and lineup data from API-Football.
Saves results to data/wc_squads.json which the Streamlit app reads at startup.

Usage:
    python3 fetch_wc_data.py

Requires: API_FOOTBALL_KEY in .env
API budget: ~55-60 requests total (1 fixture call + 48 squad calls + a few stats)
Free tier: 100 req/day — this fits in a single run.

Re-running is safe: cached results are reused so no duplicate requests.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE    = "https://v3.football.api-sports.io"
HDR     = {"x-apisports-key": API_KEY}

if not API_KEY:
    raise SystemExit("ERROR: API_FOOTBALL_KEY not set. Add it to .env first.")

CACHE_FILE   = "data/wc_fetch_cache.json"
OUTPUT_FILE  = "data/wc_squads.json"
DELAY        = 2.2   # seconds between requests (free tier: 30 req/min)

# Our 3-letter codes → API-Football team names (for display only, not for lookup)
TEAM_NAMES = {
    "ESP": "Spain",       "GER": "Germany",     "BRA": "Brazil",
    "FRA": "France",      "POR": "Portugal",    "ENG": "England",
    "ARG": "Argentina",   "BEL": "Belgium",     "SUI": "Switzerland",
    "NED": "Netherlands", "MEX": "Mexico",      "NOR": "Norway",
    "URU": "Uruguay",     "COL": "Colombia",    "AUT": "Austria",
    "USA": "USA",         "CAN": "Canada",      "ECU": "Ecuador",
    "MAR": "Morocco",     "CRO": "Croatia",     "TUR": "Turkey",
    "CIV": "Ivory Coast", "JPN": "Japan",       "EGY": "Egypt",
    "SEN": "Senegal",     "SCO": "Scotland",    "CZE": "Czech Republic",
    "KOR": "South Korea", "SWE": "Sweden",      "ALG": "Algeria",
    "PAR": "Paraguay",    "IRN": "Iran",         "BIH": "Bosnia",
    "GHA": "Ghana",       "AUS": "Australia",   "RSA": "South Africa",
    "TUN": "Tunisia",     "COD": "DR Congo",    "UZB": "Uzbekistan",
    "PAN": "Panama",      "KSA": "Saudi Arabia","NZL": "New Zealand",
    "CPV": "Cape Verde",  "QAT": "Qatar",       "JOR": "Jordan",
    "HAI": "Haiti",       "IRQ": "Iraq",        "CUW": "Curacao",
}

POSITION_MAP = {
    "Goalkeeper": "GK",
    "Defender":   "DEF",
    "Midfielder": "MID",
    "Attacker":   "FWD",
}

# ── Persistent cache (survives between runs) ──────────────────────────────────

def _load_cache() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ── API helper ────────────────────────────────────────────────────────────────

REQUESTS_MADE = 0

def _get(endpoint: str, params: dict, cache: dict, cache_key: str | None = None) -> dict:
    """GET with caching and rate-limit backoff."""
    global REQUESTS_MADE

    key = cache_key or f"{endpoint}?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    if key in cache:
        return cache[key]

    time.sleep(DELAY)
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", headers=HDR, params=params, timeout=25)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate-limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            REQUESTS_MADE += 1
            cache[key] = data
            _save_cache(cache)
            return data
        except requests.exceptions.HTTPError as e:
            print(f"  [HTTP ERROR] {endpoint} {params}: {e}")
            return {}
        except Exception as e:
            print(f"  [ERROR] {endpoint} {params}: {e}")
            return {}
    return {}


# ── Step 1: Get all 48 WC 2026 team IDs from fixtures (1 API call) ───────────

def get_team_ids_from_fixtures(cache: dict) -> dict[str, int]:
    """
    Fetch WC 2026 fixtures. Each fixture has home/away team with id and name.
    Extract all 48 team IDs in a single API call.
    Returns {team_name_lower: team_id}.
    """
    print("Step 1/3 — Fetching WC 2026 fixture list to extract team IDs...")
    data = _get("fixtures", {"league": 1, "season": 2026}, cache, "fixtures_wc2026")

    id_by_name: dict[str, int] = {}
    for fix in data.get("response", []):
        for side in ("home", "away"):
            t = fix.get("teams", {}).get(side, {})
            tid  = t.get("id")
            name = (t.get("name") or "").lower().strip()
            if tid and name:
                id_by_name[name] = tid

    print(f"  Found {len(id_by_name)} teams from fixtures.")
    return id_by_name


# Known name variants that API-Football uses (to match against our codes)
API_NAME_VARIANTS: dict[str, list[str]] = {
    "ESP": ["spain"],
    "GER": ["germany"],
    "BRA": ["brazil"],
    "FRA": ["france"],
    "POR": ["portugal"],
    "ENG": ["england"],
    "ARG": ["argentina"],
    "BEL": ["belgium"],
    "SUI": ["switzerland"],
    "NED": ["netherlands"],
    "MEX": ["mexico"],
    "NOR": ["norway"],
    "URU": ["uruguay"],
    "COL": ["colombia"],
    "AUT": ["austria"],
    "USA": ["usa", "united states", "united-states", "us"],
    "CAN": ["canada"],
    "ECU": ["ecuador"],
    "MAR": ["morocco"],
    "CRO": ["croatia"],
    "TUR": ["turkey", "türkiye"],
    "CIV": ["ivory coast", "côte d'ivoire", "cote d'ivoire"],
    "JPN": ["japan"],
    "EGY": ["egypt"],
    "SEN": ["senegal"],
    "SCO": ["scotland"],
    "CZE": ["czech republic", "czechia", "czech-republic"],
    "KOR": ["south korea", "korea republic", "korea"],
    "SWE": ["sweden"],
    "ALG": ["algeria"],
    "PAR": ["paraguay"],
    "IRN": ["iran", "ir iran"],
    "BIH": ["bosnia & herzegovina", "bosnia and herzegovina", "bosnia-herzegovina", "bosnia"],
    "GHA": ["ghana"],
    "AUS": ["australia"],
    "RSA": ["south africa"],
    "TUN": ["tunisia"],
    "COD": ["dr congo", "congo dr", "democratic republic of the congo"],
    "UZB": ["uzbekistan"],
    "PAN": ["panama"],
    "KSA": ["saudi arabia"],
    "NZL": ["new zealand"],
    "CPV": ["cape verde"],
    "QAT": ["qatar"],
    "JOR": ["jordan"],
    "HAI": ["haiti"],
    "IRQ": ["iraq"],
    "CUW": ["curacao", "curaçao"],
}


def match_team_ids(id_by_name: dict[str, int]) -> dict[str, int]:
    """Map our 3-letter codes to API team IDs."""
    result: dict[str, int] = {}
    for code, variants in API_NAME_VARIANTS.items():
        for v in variants:
            if v in id_by_name:
                result[code] = id_by_name[v]
                break
    return result


# ── Step 2: Fetch squad for each team ────────────────────────────────────────

def fetch_squad(team_id: int, cache: dict) -> list[dict]:
    data = _get("players/squads", {"team": team_id}, cache, f"squad_{team_id}")
    players = []
    for entry in data.get("response", []):
        for p in entry.get("players", []):
            pos = POSITION_MAP.get(p.get("position", ""), "MID")
            players.append({
                "id":       str(p.get("id", "")),
                "name":     p.get("name", ""),
                "position": pos,
                "age":      p.get("age"),
            })
    return players


# ── Step 3: Recent lineups for starter rates ──────────────────────────────────

def fetch_starter_rates(team_id: int, cache: dict, n: int = 5) -> tuple[dict, int]:
    """Returns ({player_id: start_count}, games_sampled)."""
    # Get last n fixtures for this team (national team only)
    data = _get("fixtures", {"team": team_id, "last": n, "type": "National"}, cache,
                f"fixtures_last{n}_{team_id}")
    # Some APIs don't support type=National; fall back without it
    if not data.get("response"):
        data = _get("fixtures", {"team": team_id, "last": n}, cache,
                    f"fixtures_last{n}_any_{team_id}")

    start_counts: dict[str, int] = {}
    games = 0

    for fix in data.get("response", []):
        fid = fix.get("fixture", {}).get("id")
        if not fid:
            continue
        lineup_data = _get("fixtures/lineups", {"fixture": fid}, cache, f"lineup_{fid}")
        for team_lineup in lineup_data.get("response", []):
            if team_lineup.get("team", {}).get("id") != team_id:
                continue
            games += 1
            for s in team_lineup.get("startXI", []):
                pid = str(s.get("player", {}).get("id", ""))
                if pid:
                    start_counts[pid] = start_counts.get(pid, 0) + 1

    return start_counts, games


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cache = _load_cache()

    # ── Step 1: team IDs ──────────────────────────────────────────────────────
    id_by_api_name = get_team_ids_from_fixtures(cache)
    team_ids = match_team_ids(id_by_api_name)

    # Show what we found / missed
    missing = [c for c in TEAM_NAMES if c not in team_ids]
    print(f"  Matched {len(team_ids)}/48 codes. Missing: {missing or 'none'}")

    if not team_ids:
        print("\nERROR: Could not match any teams. WC 2026 fixture data may not be")
        print("available yet. Try again after June 11 2026, or contact API-Sports.")
        sys.exit(1)

    # ── Step 2 + 3: Squads + lineups ─────────────────────────────────────────
    print(f"\nStep 2/3 — Fetching squads for {len(team_ids)} teams...")
    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "teams": {},
    }

    for code, tid in team_ids.items():
        print(f"  {code} (id={tid})...", end=" ", flush=True)
        squad = fetch_squad(tid, cache)

        if not squad:
            print("no squad data")
            continue

        # Try to get recent lineup data
        start_counts, games = fetch_starter_rates(tid, cache, n=5)

        squad_out = []
        for p in squad:
            pid = p["id"]
            starts = start_counts.get(pid, 0)
            rate   = (starts / games) if games > 0 else 1.0
            squad_out.append({**p, "starts": starts, "starter_rate": round(rate, 2)})

        squad_out.sort(key=lambda x: -x["starts"])
        result["teams"][code] = {
            "team_id":               tid,
            "lineup_games_sampled":  games,
            "players":               squad_out,
        }
        print(f"{len(squad_out)} players | {games} lineup games")

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    teams_with_data = len([t for t in result["teams"].values() if t["players"]])
    total_players   = sum(len(t["players"]) for t in result["teams"].values())

    print(f"\n{'='*50}")
    print(f"Saved  → {OUTPUT_FILE}")
    print(f"Teams  : {teams_with_data}/48 have squad data")
    print(f"Players: {total_players} total")
    print(f"Requests used today: {REQUESTS_MADE}")
    print(f"\nNext steps:")
    print(f"  git add data/wc_squads.json")
    print(f"  git commit -m 'Add WC 2026 squad data'")
    print(f"  git push")


if __name__ == "__main__":
    main()
