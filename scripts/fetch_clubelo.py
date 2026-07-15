#!/usr/bin/env python3
"""
Pull current club Elo ratings from clubelo.com (free, no key) and save a
name,rating CSV for the knockout Monte-Carlo — the club-football replacement
for eloratings.net national ratings.

    python3 scripts/fetch_clubelo.py                 # all clubs, today
    python3 scripts/fetch_clubelo.py --date 2026-09-15

Output: data/ucl_elo.csv with lines "ClubName,Elo" (one per club). Club names
follow ClubElo's spelling (e.g. "Man City", "Real Madrid", "Inter"); the UCL
round builder maps them to our team codes the same way build_r32.py maps
API-Football names.
"""
import argparse
import csv
import io
import os
from datetime import date

import requests

OUTPUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ucl_elo.csv"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="Ratings snapshot date YYYY-MM-DD (default today)")
    ap.add_argument("--out", default=OUTPUT, help="Output CSV path")
    args = ap.parse_args()

    day = args.date or date.today().isoformat()
    url = f"http://api.clubelo.com/{day}"
    print(f"Fetching {url} ...")
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    rows = list(csv.DictReader(io.StringIO(r.text)))
    if not rows:
        raise SystemExit("ClubElo returned no rows — check the date format (YYYY-MM-DD).")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# Club Elo ratings from api.clubelo.com snapshot {day}\n")
        f.write("# Format: ClubName,Elo — map names to team codes in the round builder.\n")
        for row in rows:
            club, elo = row.get("Club", "").strip(), row.get("Elo", "").strip()
            if club and elo:
                f.write(f"{club},{round(float(elo), 1)}\n")

    print(f"Saved {len(rows)} clubs → {args.out}")


if __name__ == "__main__":
    main()
