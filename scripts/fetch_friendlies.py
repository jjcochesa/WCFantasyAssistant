#!/usr/bin/env python3
"""
Fetch recent pre-WC international friendlies (May 15 – June 10 2026) for all 48
WC teams and extract per-player goals/assists/shots/key-passes/tackles/minutes.

Saves to data/friendlies_stats.json, which data_engine.py blends into per-90
projections at FRIENDLY_FORM_WEIGHT (config.py, default 0.30).

Run LOCALLY from your Mac (API key is IP-restricted):
    cd ~/WCFantasyAssistant
    python3 scripts/fetch_friendlies.py --key YOUR_KEY

After running:
    git add data/friendlies_stats.json
    git commit -m "Add pre-WC friendlies stats (fetch_friendlies)"
    git push origin claude/vibrant-davinci-JojAL
"""
import argparse
import json
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone

import requests

BASE  = "https://v3.football.api-sports.io"
DELAY = 2.2  # seconds between calls (free tier: 30 req/min)
CUTOFF_DATE = "2026-05-15"  # only fixtures on/after this date
WC_LEAGUE_ID = 1            # skip WC 2026 group stage matches

OUTPUT    = os.path.join(os.path.dirname(__file__), "..", "data", "friendlies_stats.json")
OUTPUT    = os.path.normpath(OUTPUT)
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "friendlies_cache.json")
CACHE_FILE = os.path.normpath(CACHE_FILE)

# Same name-matching logic as data_engine._norm_name
def _norm(name: str) -> str:
    name = name.lower().replace("ı", "i").replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


# Team code → API-Football name variants (from fetch_wc_data.py)
API_NAME_VARIANTS: dict[str, list[str]] = {
    "ESP": ["spain"],           "GER": ["germany"],         "BRA": ["brazil"],
    "FRA": ["france"],          "POR": ["portugal"],        "ENG": ["england"],
    "ARG": ["argentina"],       "BEL": ["belgium"],         "SUI": ["switzerland"],
    "NED": ["netherlands"],     "MEX": ["mexico"],          "NOR": ["norway"],
    "URU": ["uruguay"],         "COL": ["colombia"],        "AUT": ["austria"],
    "USA": ["usa", "united states", "us"], "CAN": ["canada"], "ECU": ["ecuador"],
    "MAR": ["morocco"],         "CRO": ["croatia"],         "TUR": ["turkey", "türkiye"],
    "CIV": ["ivory coast", "côte d'ivoire", "cote d'ivoire"],
    "JPN": ["japan"],           "EGY": ["egypt"],           "SEN": ["senegal"],
    "SCO": ["scotland"],        "CZE": ["czech republic", "czechia"],
    "KOR": ["south korea", "korea republic"],
    "SWE": ["sweden"],          "ALG": ["algeria"],         "PAR": ["paraguay"],
    "IRN": ["iran", "ir iran"], "BIH": ["bosnia & herzegovina", "bosnia and herzegovina", "bosnia"],
    "GHA": ["ghana"],           "AUS": ["australia"],       "RSA": ["south africa"],
    "TUN": ["tunisia"],         "COD": ["dr congo", "congo dr"],
    "UZB": ["uzbekistan"],      "PAN": ["panama"],          "KSA": ["saudi arabia"],
    "NZL": ["new zealand"],     "CPV": ["cape verde"],      "QAT": ["qatar"],
    "JOR": ["jordan"],          "HAI": ["haiti"],           "IRQ": ["iraq"],
    "CUW": ["curacao", "curaçao"],
}


# ── Cache ─────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
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


_REQUESTS_MADE = 0

def _get(endpoint: str, params: dict, cache: dict, key: str, headers: dict) -> dict:
    global _REQUESTS_MADE
    if key in cache:
        return cache[key]
    time.sleep(DELAY)
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", headers=headers, params=params, timeout=25)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate-limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            _REQUESTS_MADE += 1
            cache[key] = data
            _save_cache(cache)
            return data
        except Exception as e:
            print(f"  [ERR] {endpoint} {params}: {e}")
            return {}
    return {}


# ── Step 1: get API-Football team IDs from WC 2026 fixtures ──────────────────

def get_team_ids(cache: dict, headers: dict) -> dict[str, int]:
    print("Step 1/3 — Fetching WC 2026 fixtures to get team IDs...")
    data = _get("fixtures", {"league": WC_LEAGUE_ID, "season": 2026},
                cache, "wc2026_fixtures", headers)
    id_by_name: dict[str, int] = {}
    for fix in data.get("response", []):
        for side in ("home", "away"):
            t = fix.get("teams", {}).get(side, {})
            tid  = t.get("id")
            name = (t.get("name") or "").lower().strip()
            if tid and name:
                id_by_name[name] = tid

    result: dict[str, int] = {}
    for code, variants in API_NAME_VARIANTS.items():
        for v in variants:
            if v in id_by_name:
                result[code] = id_by_name[v]
                break

    print(f"  Matched {len(result)}/48 team codes.")
    if len(result) < 30:
        print("  WARNING: low match count — WC fixtures may not be published yet or "
              "API-Football data is incomplete.")
    return result


# ── Step 2: get recent international fixtures per team ───────────────────────

def get_recent_intl_fixtures(team_id: int, code: str, cache: dict, headers: dict) -> list[dict]:
    data = _get("fixtures", {"team": team_id, "last": 5},
                cache, f"last5_{team_id}", headers)
    qualifying = []
    for fix in data.get("response", []):
        league    = fix.get("league", {})
        fixture   = fix.get("fixture", {})
        date_str  = (fixture.get("date") or "")[:10]  # "YYYY-MM-DD"
        league_id = league.get("id")
        league_name = (league.get("name") or "").lower()

        # Only post-cutoff dates
        if date_str < CUTOFF_DATE:
            continue
        # Skip WC 2026 group stage (starts June 11)
        if league_id == WC_LEAGUE_ID:
            continue
        # Keep only international competitions (league type or name filter)
        league_type = (league.get("type") or "").lower()
        is_intl = (league_type == "international"
                   or "friend" in league_name
                   or "nations" in league_name
                   or "qualification" in league_name
                   or "qualifier" in league_name)
        if not is_intl:
            continue

        fid = fixture.get("id")
        if fid:
            qualifying.append({
                "fixture_id": fid,
                "date": date_str,
                "league": league.get("name"),
                "home": fix.get("teams", {}).get("home", {}).get("name"),
                "away": fix.get("teams", {}).get("away", {}).get("name"),
            })

    return qualifying


# ── Step 3: extract per-player stats from a fixture ──────────────────────────

def get_player_stats(fixture_id: int, team_id: int, cache: dict, headers: dict) -> list[dict]:
    data = _get("fixtures/players", {"fixture": fixture_id, "team": team_id},
                cache, f"fplayers_{fixture_id}_{team_id}", headers)
    players = []
    for team_block in data.get("response", []):
        if team_block.get("team", {}).get("id") != team_id:
            continue
        for entry in team_block.get("players", []):
            p = entry.get("player", {})
            s = (entry.get("statistics") or [{}])[0]
            mins = s.get("games", {}).get("minutes") or 0
            if mins == 0:
                continue
            players.append({
                "name":       p.get("name", ""),
                "goals":      s.get("goals", {}).get("total")   or 0,
                "assists":    s.get("goals", {}).get("assists")  or 0,
                "shots_on":   s.get("shots", {}).get("on")      or 0,
                "key_passes": s.get("passes", {}).get("key")    or 0,
                "tackles":    s.get("tackles", {}).get("total") or 0,
                "minutes":    mins,
            })
    return players


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="API-Football key")
    parser.add_argument("--min-minutes", type=int, default=30,
                        help="Minimum total minutes across friendlies to include a player (default 30)")
    args = parser.parse_args()

    headers = {"x-apisports-key": args.key}
    cache   = _load_cache()

    # Step 1: team IDs
    team_ids = get_team_ids(cache, headers)
    if not team_ids:
        print("ERROR: Could not resolve any team IDs. Aborting.")
        sys.exit(1)

    # Step 2 + 3: fixtures → player stats
    print(f"\nStep 2/3 — Fetching recent friendly fixtures and player stats...")
    accumulated: dict[str, dict] = {}  # norm_name → aggregated stats

    teams_with_data = 0
    for code, tid in sorted(team_ids.items()):
        fixtures = get_recent_intl_fixtures(tid, code, cache, headers)
        if not fixtures:
            print(f"  {code}: no recent international fixtures found")
            continue

        print(f"  {code}: {len(fixtures)} fixture(s) — ", end="", flush=True)
        players_before = sum(1 for v in accumulated.values() if v["team_code"] == code)
        for fix in fixtures[:3]:  # cap at 3 to limit API usage
            stats_list = get_player_stats(fix["fixture_id"], tid, cache, headers)
            for s in stats_list:
                key = _norm(s["name"])
                if key not in accumulated:
                    accumulated[key] = {
                        "display_name": s["name"],
                        "team_code":    code,
                        "goals":        0,
                        "assists":      0,
                        "shots_on":     0,
                        "key_passes":   0,
                        "tackles":      0,
                        "minutes":      0,
                        "matches":      0,
                    }
                acc = accumulated[key]
                acc["goals"]      += s["goals"]
                acc["assists"]    += s["assists"]
                acc["shots_on"]   += s["shots_on"]
                acc["key_passes"] += s["key_passes"]
                acc["tackles"]    += s["tackles"]
                acc["minutes"]    += s["minutes"]
                acc["matches"]    += 1

        team_players = sum(1 for v in accumulated.values() if v["team_code"] == code)
        print(f"{team_players} players")
        teams_with_data += 1

    # Filter to minimum minutes
    before = len(accumulated)
    accumulated = {k: v for k, v in accumulated.items() if v["minutes"] >= args.min_minutes}
    print(f"\nPlayers with >={args.min_minutes} min: {len(accumulated)} / {before}")

    # Build output
    output = {
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
        "cutoff_date":  CUTOFF_DATE,
        "teams_found":  teams_with_data,
        "api_requests": _REQUESTS_MADE,
        "players":      accumulated,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved → {OUTPUT}  ({len(accumulated)} players, {os.path.getsize(OUTPUT)//1024}KB)")
    print(f"API requests used: {_REQUESTS_MADE}")
    print("\nNext steps:")
    print("  git add data/friendlies_stats.json data/friendlies_cache.json")
    print("  git commit -m 'Add pre-WC friendlies stats'")
    print("  git push origin claude/vibrant-davinci-JojAL")


if __name__ == "__main__":
    main()
