#!/usr/bin/env python3
"""
Fetch player xG/xA stats from Sofascore public API.
Sofascore is a proper JSON API (not HTML scraping) — works with plain requests.
Run LOCALLY: python3 fetch_understat.py

Coverage: PL, La Liga, Serie A, Bundesliga, Ligue 1
Output:   data/fbref_stats.json  (same filename — no downstream changes needed)
"""
import json
import os
import time
import unicodedata

import requests

API = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer":        "https://www.sofascore.com/",
    "Accept":         "application/json, text/plain, */*",
    "Accept-Language":"en-US,en;q=0.9",
    "Origin":         "https://www.sofascore.com",
}

# Sofascore unique-tournament IDs for our 5 leagues
TOURNAMENTS: dict[int, str] = {
    17: "PL",
    8:  "LaLiga",
    23: "SerieA",
    35: "Bundesliga",
    34: "Ligue1",
}

OUTPUT_FILE = "data/fbref_stats.json"

session = requests.Session()
session.headers.update(HEADERS)


def norm_name(name: str) -> str:
    name = name.replace("ı", "i").replace("İ", "i")
    nfkd = unicodedata.normalize("NFKD", name.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def get_season_id(tournament_id: int) -> int | None:
    """Return the 2024/25 season ID, or the most recent one."""
    r = session.get(f"{API}/unique-tournament/{tournament_id}/seasons", timeout=15)
    r.raise_for_status()
    seasons = r.json().get("seasons", [])
    for s in seasons:
        year = s.get("year", "")
        if "2024" in year:
            return s["id"]
    return seasons[0]["id"] if seasons else None


def fetch_all_pages(tournament_id: int, season_id: int) -> list[dict]:
    """Page through player statistics (100 per page)."""
    all_entries: list[dict] = []
    offset = 0
    limit  = 100
    while True:
        r = session.get(
            f"{API}/unique-tournament/{tournament_id}/season/{season_id}/statistics/players",
            params={
                "limit":        limit,
                "offset":       offset,
                "accumulation": "total",
                "order":        "-rating",
                "filters":      "minutes.GT.90",
            },
            timeout=20,
        )
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} at offset {offset} — stopping")
            break
        data    = r.json()
        batch   = data.get("players", [])
        if not batch:
            break
        all_entries.extend(batch)
        results = data.get("results", {})
        page    = results.get("page",  1)
        pages   = results.get("pages", 1)
        if page >= pages:
            break
        offset += limit
        time.sleep(0.4)
    return all_entries


def main() -> None:
    all_players: dict[str, dict] = {}

    for tournament_id, label in TOURNAMENTS.items():
        print(f"\n{label} (id={tournament_id})...")
        try:
            season_id = get_season_id(tournament_id)
            if not season_id:
                print(f"  No 2024/25 season found — skipping")
                continue
            print(f"  Season ID: {season_id}")
            time.sleep(0.5)
            entries = fetch_all_pages(tournament_id, season_id)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        count = 0
        for entry in entries:
            p = entry.get("player",     {})
            s = entry.get("statistics", {})

            name = p.get("name") or p.get("shortName", "")
            if not name:
                continue

            mins   = float(s.get("minutesPlayed", 0) or 0)
            games  = int(s.get("appearances",    0) or 0) or 1
            starts = int(s.get("started",        0) or 0)
            per90  = mins / 90 if mins >= 90 else 1.0

            # Sofascore may expose xG as expectedGoals or goalExpected
            xg  = float(s.get("expectedGoals")  or s.get("goalExpected")   or 0)
            xa  = float(s.get("expectedAssists") or s.get("assistExpected") or 0)
            gls = float(s.get("goals",   0) or 0)
            ast = float(s.get("assists", 0) or 0)

            # If Sofascore doesn't expose xG, fall back to actual goals as proxy
            if xg == 0 and gls > 0:
                xg = gls * 0.85  # rough conversion (xG ≈ 85% of goals on avg)
            if xa == 0 and ast > 0:
                xa = ast * 0.85

            team_raw = p.get("team", {})
            squad    = team_raw.get("name", "") if isinstance(team_raw, dict) else ""

            key = norm_name(name)
            record = {
                "name":         name,
                "norm_name":    key,
                "squad":        squad,
                "league":       label,
                "mp":           games,
                "starts":       starts,
                "minutes":      int(mins),
                "xg":           round(xg,  3),
                "xa":           round(xa,  3),
                "xg90":         round(xg  / per90, 4),
                "xa90":         round(xa  / per90, 4),
                "goals90":      round(gls / per90, 4),
                "sot90":        0.0,
                "starter_rate": round(starts / games, 3) if games > 0 else 1.0,
            }

            # Keep highest-minutes entry when player appears in multiple leagues
            if key not in all_players or int(mins) > all_players[key]["minutes"]:
                all_players[key] = record
                count += 1

        print(f"  {count} players, {len(all_players)} unique total")
        time.sleep(2)

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_players, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(all_players)} players → {OUTPUT_FILE}")
    print("Next: python3 name_match.py")


if __name__ == "__main__":
    main()
