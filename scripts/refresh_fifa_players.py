#!/usr/bin/env python3
"""
Refresh data/fifa_players.json from the live FIFA Fantasy feed.

Run this LOCALLY (from your Mac) before the tournament — cloud can't reach
the endpoint (IP-restricted 403).

Usage:
    python3 scripts/refresh_fifa_players.py
    python3 scripts/refresh_fifa_players.py --token "Bearer eyJ..."

If unauthenticated fetch fails, log into play.fifa.com in your browser,
open DevTools → Network, filter for "players.json", copy the Authorization
header value, and pass it via --token.

After running:
    git add data/fifa_players.json
    git commit -m "Refresh FIFA Fantasy player data — WC 2026 finalized squads"
    git push
"""
import argparse
import json
import sys
import os
import requests
from datetime import datetime, timezone

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "fifa_players.json")
OUTPUT = os.path.normpath(OUTPUT)

CANDIDATE_URLS = [
    "https://play.fifa.com/json/fantasy/players.json",
    "https://gaming.fifa.com/api/en/fantasy/v2/players",
    "https://gaming.fifa.com/api/en/fantasy/v1/players",
    "https://gaming.fifa.com/api/en/fantasy/players",
]

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Referer": "https://play.fifa.com/fantasy/",
}


def fetch(token: str | None) -> list:
    headers = dict(BASE_HEADERS)
    if token:
        headers["Authorization"] = token if token.startswith("Bearer") else f"Bearer {token}"

    for url in CANDIDATE_URLS:
        print(f"Trying {url} ...", end=" ", flush=True)
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(r.status_code)
            if r.status_code != 200:
                continue
            data = r.json()
            players = data if isinstance(data, list) else (
                data.get("players") or data.get("data") or data.get("response") or []
            )
            if players:
                return players
        except Exception as e:
            print(f"ERROR: {e}")

    return []


def summarize(players: list) -> None:
    from collections import Counter
    statuses = Counter(p.get("status", "?") for p in players)
    squads = Counter(p.get("squadId") for p in players if p.get("status") != "transferred")
    over26 = {k: v for k, v in squads.items() if v > 26}
    print(f"\nTotal players : {len(players)}")
    print(f"Statuses      : {dict(statuses)}")
    print(f"Playing squads: {len(squads)}")
    if over26:
        print(f"Still >26     : {len(over26)} teams (squads not yet finalized in feed)")
    else:
        print("All squads    : 26 or fewer players — looks fully finalized!")
    transferred = [p for p in players if p.get("status") == "transferred"]
    if transferred:
        print(f"\nTransferred/cut players ({len(transferred)}):")
        for p in transferred:
            name = p.get("knownName") or f"{p.get('firstName','')} {p.get('lastName','')}".strip()
            print(f"  {name} | squad {p.get('squadId')} | {p.get('position')} | {p.get('price')}")


def compare_with_existing(new_players: list) -> None:
    if not os.path.exists(OUTPUT):
        return
    try:
        old = json.load(open(OUTPUT))
        old_ids = {str(p.get("id")) for p in old}
        new_ids = {str(p.get("id")) for p in new_players}
        added = new_ids - old_ids
        removed = old_ids - new_ids
        old_transferred = {str(p.get("id")) for p in old if p.get("status") == "transferred"}
        new_transferred = {str(p.get("id")) for p in new_players if p.get("status") == "transferred"}
        newly_cut = new_transferred - old_transferred
        if added:
            print(f"\nNew players added  : {len(added)}")
        if removed:
            print(f"Players removed    : {len(removed)}")
        if newly_cut:
            print(f"Newly cut (new transferred): {len(newly_cut)}")
            cut_map = {str(p.get("id")): p for p in new_players}
            for pid in newly_cut:
                p = cut_map.get(pid, {})
                name = p.get("knownName") or f"{p.get('firstName','')} {p.get('lastName','')}".strip()
                print(f"  CUT: {name} | squad {p.get('squadId')} | {p.get('position')}")
        if not added and not removed and not newly_cut:
            print("\nNo changes vs existing fifa_players.json.")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Refresh data/fifa_players.json from FIFA Fantasy")
    parser.add_argument("--token", default=None, help="Bearer token from play.fifa.com DevTools")
    args = parser.parse_args()

    players = fetch(args.token)
    if not players:
        print("\nFailed to fetch player data from all endpoints.")
        print("Try: python3 scripts/refresh_fifa_players.py --token 'Bearer eyJ...'")
        print("(Get token from: play.fifa.com → DevTools → Network → players.json → Authorization header)")
        sys.exit(1)

    compare_with_existing(players)
    summarize(players)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"\nSaved → {OUTPUT}  ({len(players)} players, {os.path.getsize(OUTPUT)//1024}KB)")
    print(f"Fetched at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("\nNext steps:")
    print("  git add data/fifa_players.json")
    print("  git commit -m 'Refresh FIFA Fantasy players — WC 2026 finalized squads'")
    print("  git push")


if __name__ == "__main__":
    main()
