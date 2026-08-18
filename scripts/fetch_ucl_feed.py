#!/usr/bin/env python3
"""
Pull the official UEFA Champions League Fantasy player feed (prices, positions,
clubs, ownership) → data/ucl_players.json — the UCL replacement for the FIFA
fantasy feed (data/fifa_players.json).

    python3 scripts/fetch_ucl_feed.py
    python3 scripts/fetch_ucl_feed.py --url <feed-url>   # if the default 404s

The feed is public JSON (no auth), but UEFA shuffles the path each season and
per gameweek. Known pattern from recent seasons:

    https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_{TOUR}_en_{GW}.json

where TOUR is the season's tour id and GW the gameweek number. When the 2026-27
game opens (August), open gaming.uefa.com/en/uclfantasy with browser DevTools →
Network tab, filter "players", and copy the real URL here (or pass --url).
This script tries a few candidate URLs and reports what it finds.
"""
import argparse
import json
import os

import requests

OUTPUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ucl_players.json"))

# Candidate tour ids to probe — bump when the new season's id is known.
CANDIDATE_URLS = [
    "https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_80_en_1.json",
    "https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_70_en_1.json",
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


def try_fetch(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            print(f"  {r.status_code} — {url}")
            return None
        data = r.json()
        # Feed shape: {"data": {"value": {"playerList": [...]}}} in recent seasons
        players = (((data.get("data") or {}).get("value") or {}).get("playerList")
                   or data.get("playerList") or [])
        if not players:
            print(f"  200 but no playerList — {url}")
            return None
        return players
    except Exception as e:
        print(f"  ERR {e} — {url}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="Exact feed URL (from browser DevTools)")
    ap.add_argument("--out", default=OUTPUT)
    args = ap.parse_args()

    urls = [args.url] if args.url else CANDIDATE_URLS
    players = None
    for u in urls:
        print(f"Trying {u}")
        players = try_fetch(u)
        if players:
            break
    if not players:
        raise SystemExit(
            "No feed found. Once the 26-27 game opens: gaming.uefa.com/en/uclfantasy "
            "→ DevTools → Network → filter 'players' → copy URL → rerun with --url."
        )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(players)} players → {args.out}")
    # Quick shape peek so we can wire the loader without guessing
    sample = players[0]
    print("Sample keys:", sorted(sample.keys())[:20])


if __name__ == "__main__":
    main()
