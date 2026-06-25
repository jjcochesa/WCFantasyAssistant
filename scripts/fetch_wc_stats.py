#!/usr/bin/env python3
"""
Fetch accumulated REAL World Cup 2026 stats (league=1) for every team and extract
per-player goals/assists/shots/key-passes/tackles/minutes across all matches played
so far. Run after each round completes.

Saves to data/wc_stats.json, which data_engine.py blends into per-90 projections
at a weight that ramps with WC minutes played (config.WC_FORM_*).

Run LOCALLY from your Mac (API key is IP-restricted):
    cd ~/WCFantasyAssistant
    python3 scripts/fetch_wc_stats.py --key YOUR_KEY

After running:
    git add data/wc_stats.json
    git commit -m "Add WC stats through <round>"
    git push origin claude/vibrant-davinci-JojAL

API budget: 1 call for the fixture list + 1 call per (finished fixture × 2 teams).
After MD1 that's ~1 + 24×2 = ~49 calls. Cheap. Results are cached so re-runs only
fetch newly-finished fixtures.
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
DELAY = 2.2          # seconds between calls (free tier: 30 req/min)
WC_LEAGUE_ID = 1     # FIFA World Cup 2026
WC_SEASON    = 2026

# API-Football team names → our canonical names (data/team_stats.py TEAM_NAMES)
_TEAM_NAME_MAP = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde Islands":   "Cape Verde",
    "Congo DR":             "DR Congo",
    "Curaçao":              "Curacao",
    "Czechia":              "Czech Republic",
    "Türkiye":              "Turkey",
}

OUTPUT     = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "wc_stats.json"))
CACHE_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "wc_fetch_cache.json"))


# Same name-matching logic as data_engine._norm_name
def _norm(name: str) -> str:
    name = name.lower().replace("ı", "i").replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


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

def _get(endpoint: str, params: dict, cache: dict, key: str, headers: dict,
         allow_cache: bool = True) -> dict:
    global _REQUESTS_MADE
    if allow_cache and key in cache:
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


# ── Step 1: list finished WC fixtures ────────────────────────────────────────

def get_finished_fixtures(cache: dict, headers: dict) -> list[dict]:
    """Fetch the full WC fixture list fresh each run (so newly-finished games show up)."""
    print("Step 1/2 — Fetching WC 2026 fixtures...")
    data = _get("fixtures", {"league": WC_LEAGUE_ID, "season": WC_SEASON},
                cache, "wc_fixtures_live", headers, allow_cache=False)
    finished = []
    for fix in data.get("response", []):
        fixture = fix.get("fixture", {})
        status  = (fixture.get("status", {}) or {}).get("short", "")
        # FT / AET / PEN = match complete
        if status not in ("FT", "AET", "PEN"):
            continue
        fid = fixture.get("id")
        home = fix.get("teams", {}).get("home", {})
        away = fix.get("teams", {}).get("away", {})
        if fid:
            finished.append({
                "fixture_id": fid,
                "date": (fixture.get("date") or "")[:10],
                "round": (fix.get("league", {}) or {}).get("round", ""),
                "home_id": home.get("id"),
                "home": _TEAM_NAME_MAP.get(home.get("name"), home.get("name")),
                "away_id": away.get("id"),
                "away": _TEAM_NAME_MAP.get(away.get("name"), away.get("name")),
            })
    print(f"  {len(finished)} finished fixture(s).")
    return finished


# ── Step 2: extract per-player stats from a fixture/team ──────────────────────

def get_player_stats(fixture_id: int, team_id: int, cache: dict, headers: dict,
                     allow_cache: bool = True) -> list[dict]:
    data = _get("fixtures/players", {"fixture": fixture_id, "team": team_id},
                cache, f"wcplayers_{fixture_id}_{team_id}", headers, allow_cache=allow_cache)
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
    parser.add_argument("--min-minutes", type=int, default=1,
                        help="Minimum total WC minutes to include a player (default 1)")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-pull player stats for ALL finished fixtures, bypassing the "
                             "per-fixture cache. Use once per round to correct any fixtures "
                             "that were cached before the API finished updating minutes.")
    args = parser.parse_args()

    headers = {"x-apisports-key": args.key}
    cache   = _load_cache()

    fixtures = get_finished_fixtures(cache, headers)
    if not fixtures:
        print("No finished WC fixtures yet — nothing to do.")
        sys.exit(0)

    print(f"\nStep 2/2 — Extracting per-player stats from {len(fixtures)} fixture(s)...")
    accumulated: dict[str, dict] = {}  # norm_name → aggregated stats
    last_round = ""

    for fix in fixtures:
        last_round = fix.get("round") or last_round
        for side in ("home", "away"):
            tid  = fix[f"{side}_id"]
            tnam = fix[side]
            if not tid:
                continue
            stats_list = get_player_stats(fix["fixture_id"], tid, cache, headers,
                                          allow_cache=not args.refresh)
            for s in stats_list:
                key = _norm(s["name"])
                if key not in accumulated:
                    accumulated[key] = {
                        "display_name": s["name"],
                        "team":       tnam,
                        "goals":      0, "assists":    0, "shots_on":   0,
                        "key_passes": 0, "tackles":    0, "minutes":    0,
                        "matches":    0,
                    }
                acc = accumulated[key]
                acc["goals"]      += s["goals"]
                acc["assists"]    += s["assists"]
                acc["shots_on"]   += s["shots_on"]
                acc["key_passes"] += s["key_passes"]
                acc["tackles"]    += s["tackles"]
                acc["minutes"]    += s["minutes"]
                acc["matches"]    += 1

    before = len(accumulated)
    accumulated = {k: v for k, v in accumulated.items() if v["minutes"] >= args.min_minutes}
    print(f"\nPlayers with >={args.min_minutes} min: {len(accumulated)} / {before}")

    output = {
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
        "through_round":  last_round,
        "fixtures_used":  len(fixtures),
        "api_requests":   _REQUESTS_MADE,
        "players":        accumulated,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved → {OUTPUT}  ({len(accumulated)} players, {os.path.getsize(OUTPUT)//1024}KB)")
    print(f"API requests used this run: {_REQUESTS_MADE}")
    print("\nNext steps:")
    print("  git add data/wc_stats.json")
    print("  git commit -m 'Add WC stats'")
    print("  git push origin claude/vibrant-davinci-JojAL")


if __name__ == "__main__":
    main()
