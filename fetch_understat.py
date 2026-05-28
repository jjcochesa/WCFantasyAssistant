#!/usr/bin/env python3
"""
Fetch player xG/xA stats from Understat (no Cloudflare, plain requests).
Run LOCALLY: python3 fetch_understat.py

Coverage: PL, La Liga, Serie A, Bundesliga, Ligue 1 (~85% of high-priced WC players)
Output:   data/fbref_stats.json   (dict keyed by norm_name — same file name as
          the old FBref script so name_match.py and data_engine.py need no changes)

Understat embeds player data as JSON.parse('...') in the page HTML.
"""
import json
import re
import sys
import time
import unicodedata

import requests

UNDERSTAT_BASE = "https://understat.com"

LEAGUES = {
    "EPL":        "EPL",
    "La_liga":    "La_liga",
    "Serie_A":    "Serie_A",
    "Bundesliga": "Bundesliga",
    "Ligue_1":    "Ligue_1",
}

SEASON = 2024   # 2024/25 season on Understat

OUTPUT_FILE = "data/fbref_stats.json"

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0"


def norm_name(name: str) -> str:
    name = name.replace("ı", "i").replace("İ", "i")
    nfkd = unicodedata.normalize("NFKD", name.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def fetch_league(league: str, season: int) -> dict:
    url = f"{UNDERSTAT_BASE}/league/{league}/{season}"
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return {}

    match = re.search(r"var\s+playersData\s*=\s*JSON\.parse\('(.+?)'\)", r.text)
    if not match:
        print(f"  [WARN] playersData not found in {url}")
        return {}

    raw = match.group(1).encode("raw_unicode_escape").decode("unicode_escape")
    try:
        players = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error: {e}")
        return {}

    result = {}
    for p in players:
        name = p.get("player_name", "")
        if not name:
            continue

        mins    = float(p.get("time")   or 0)
        games   = int(p.get("games")    or 1)
        starts  = int(p.get("starts")   or 0)
        per90   = mins / 90 if mins >= 45 else 1.0

        xg_raw  = float(p.get("xG")  or 0)
        xa_raw  = float(p.get("xA")  or 0)

        result[norm_name(name)] = {
            "name":         name,
            "norm_name":    norm_name(name),
            "squad":        p.get("team_title", ""),
            "league":       league,
            "xg":           round(xg_raw, 3),
            "xa":           round(xa_raw, 3),
            "xg90":         round(xg_raw / per90, 4),
            "xa90":         round(xa_raw / per90, 4),
            "goals90":      round(int(p.get("goals") or 0) / per90, 4),
            "sot90":        0.0,   # not available from Understat
            "goals":        int(p.get("goals")   or 0),
            "assists":      int(p.get("assists")  or 0),
            "shots":        int(p.get("shots")    or 0),
            "minutes":      int(mins),
            "mp":           games,
            "starts":       starts,
            "starter_rate": round(starts / games, 3) if games > 0 else 1.0,
        }
    return result


def main() -> None:
    all_players: dict = {}

    for label, slug in LEAGUES.items():
        print(f"Fetching {label}...")
        data = fetch_league(slug, SEASON)
        print(f"  {len(data)} players")

        # Keep higher-minutes entry when a player appears in two leagues
        for k, v in data.items():
            if k not in all_players or v["minutes"] > all_players[k]["minutes"]:
                all_players[k] = v

        time.sleep(3)

    import os
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_players, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(all_players)} players → {OUTPUT_FILE}")
    print("Next: python3 name_match.py")


if __name__ == "__main__":
    main()
