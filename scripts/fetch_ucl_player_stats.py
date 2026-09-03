#!/usr/bin/env python3
"""
Pull 2025-26 player stats across ALL competitions for every club in the UCL
league phase, from API-Football, and aggregate them per player.

    python3 scripts/fetch_ucl_player_stats.py --key YOUR_KEY
    python3 scripts/fetch_ucl_player_stats.py --key YOUR_KEY --season 2025
    python3 scripts/fetch_ucl_player_stats.py --clubs RMA,BAY   # just a couple

Why all competitions: a player's Champions League record is 8-13 games at best
and missing entirely for anyone whose club didn't qualify last season. Domestic
league + cup minutes cover the whole pool with a far larger sample, which is
what the per-90 model actually wants.

API-Football returns one statistics block per competition per player, so each
player's blocks are summed into a single season total.

Output: data/ucl_player_stats.json, keyed by normalised name:
    {"kylian mbappe": {"team": "RMA", "minutes": 3210, "goals": 41, ...}}

Budget: ~2-4 calls per club (paginated), so roughly 100-150 calls for 36 clubs.
Team ids are resolved once and cached in data/apif_ucl_team_ids.json.

Run LOCALLY — the API key is IP-restricted to the owner's machine.
"""
import argparse
import json
import os
import sys
import time
import unicodedata

import requests

BASE = "https://v3.football.api-sports.io"
DELAY = 2.2

HERE = os.path.dirname(__file__)
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
OUTPUT = os.path.join(DATA, "ucl_player_stats.json")
TEAM_ID_CACHE = os.path.join(DATA, "apif_ucl_team_ids.json")

sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
from data.ucl_draw import CLUBS  # noqa: E402

# What to type into API-Football's team search for each of our club codes.
SEARCH_NAMES = {
    "PSG": "Paris Saint Germain", "BAY": "Bayern Munich", "RMA": "Real Madrid",
    "LIV": "Liverpool", "INT": "Inter", "MCI": "Manchester City",
    "ARS": "Arsenal", "BAR": "Barcelona", "ATM": "Atletico Madrid",
    "DOR": "Borussia Dortmund", "ROM": "AS Roma", "SPO": "Sporting CP",
    "AVL": "Aston Villa", "POR": "FC Porto", "MUN": "Manchester United",
    "CLB": "Club Brugge KV", "BET": "Real Betis", "PSV": "PSV Eindhoven",
    "FEY": "Feyenoord", "LIL": "Lille", "BOD": "Bodo Glimt", "NAP": "Napoli",
    "RBL": "RB Leipzig", "VIL": "Villarreal", "FEN": "Fenerbahce",
    "SHK": "Shakhtar Donetsk", "GAL": "Galatasaray", "SLA": "Slavia Praha",
    "SLB": "Slovan Bratislava", "STU": "VfB Stuttgart", "AEK": "AEK Athens",
    "LSK": "LASK", "COM": "Como", "LEN": "Lens", "VIK": "Viking",
    "SAB": "Sabah",
}

# The country each club plays in. A name search alone is not safe: "Bayern
# Munich" returns the women's team first, and "LASK" substring-matches Slask
# Wroclaw in Poland. Both resolved silently to the wrong squad. Country is the
# cheap discriminator that rules those out.
TEAM_COUNTRY = {
    "AEK": "Greece", "ARS": "England", "ATM": "Spain", "AVL": "England",
    "BAR": "Spain", "BAY": "Germany", "BET": "Spain", "BOD": "Norway",
    "CLB": "Belgium", "COM": "Italy", "DOR": "Germany", "FEN": "Turkey",
    "FEY": "Netherlands", "GAL": "Turkey", "INT": "Italy", "LEN": "France",
    "LIL": "France", "LIV": "England", "LSK": "Austria", "MCI": "England",
    "MUN": "England", "NAP": "Italy", "POR": "Portugal", "PSG": "France",
    "PSV": "Netherlands", "RBL": "Germany", "RMA": "Spain", "ROM": "Italy",
    "SAB": "Azerbaijan", "SHK": "Ukraine", "SLA": "Czech-Republic",
    "SLB": "Slovakia", "SPO": "Portugal", "STU": "Germany", "VIK": "Norway",
    "VIL": "Spain",
}

# API-Football has renamed a few of these over the years; accept either spelling.
COUNTRY_ALIASES = {
    "turkey": {"turkey", "turkiye", "türkiye"},
    "czech-republic": {"czech-republic", "czech republic", "czechia"},
}

_REQS = 0


def _same_country(got: str, want: str) -> bool:
    g = (got or "").strip().lower().replace("-", " ")
    w = (want or "").strip().lower().replace("-", " ")
    if not g or not w:
        return False
    if g == w:
        return True
    for canon, spellings in COUNTRY_ALIASES.items():
        flat = {s.replace("-", " ") for s in spellings}
        if w in flat and g in flat:
            return True
    return False


def _is_not_the_first_team(name: str) -> bool:
    """Women's, youth and reserve sides share their club's name and outrank it
    in search results often enough to matter."""
    n = f" {(name or '').lower().strip()} "
    if any(t in n for t in (" w ", " women ", " feminin", " femenino", " ladies ")):
        return True
    if any(t in n for t in (" u19 ", " u20 ", " u21 ", " u23 ", " youth ",
                            " academy ", " reserve", " ii ", " b ")):
        return True
    return False


def _norm(name: str) -> str:
    n = (name or "").lower().replace("ı", "i").replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return " ".join(n.replace("-", " ").replace(".", "").replace("'", "").split())


def _get(endpoint: str, params: dict, headers: dict) -> dict:
    global _REQS
    time.sleep(DELAY)
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", headers=headers, params=params, timeout=30)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"    rate-limited, waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            if data.get("errors"):
                print(f"    [API errors] {data['errors']}")
            _REQS += 1
            return data
        except Exception as e:
            wait = 3 * (attempt + 1)
            print(f"    [retry {attempt+1}/4] {endpoint} {params}: {e} — waiting {wait}s")
            time.sleep(wait)
    print(f"    [ERR] gave up on {endpoint} {params}")
    return {}


def resolve_team_ids(codes: list, headers: dict) -> dict:
    """code -> API-Football team id, cached so this costs nothing on re-runs."""
    cache = {}
    if os.path.exists(TEAM_ID_CACHE):
        try:
            cache = json.load(open(TEAM_ID_CACHE))
        except Exception:
            cache = {}
    missing = [c for c in codes if c not in cache]
    if missing:
        print(f"Resolving {len(missing)} team id(s)...")
    for code in missing:
        term = SEARCH_NAMES.get(code, CLUBS.get(code, code))
        # The search field accepts only alphanumerics and spaces — a slash in
        # "Bodo/Glimt" made the whole query fail.
        term = " ".join("".join(ch if ch.isalnum() or ch.isspace() else " "
                                for ch in term).split())
        data = _get("teams", {"search": term}, headers)
        resp = data.get("response") or []
        if not resp:
            print(f"  [WARN] no API-Football team found for {code} ({term!r})")
            continue

        want_country = TEAM_COUNTRY.get(code)
        # Rank candidates rather than taking the first hit. Country is the
        # strongest signal, then an exact name match; women's/youth/reserve
        # sides are pushed to the bottom because they share the club's name.
        def rank(item):
            t = item.get("team") or {}
            name = t.get("name") or ""
            return (
                0 if (want_country and _same_country(t.get("country"), want_country)) else 1,
                1 if _is_not_the_first_team(name) else 0,
                0 if _norm(name) == _norm(term) else 1,
                len(name),
            )

        best = min(resp, key=rank)
        t = best.get("team") or {}
        tid, tname, tcountry = t.get("id"), t.get("name"), t.get("country")
        if not tid:
            print(f"  [WARN] no usable team id for {code} ({term!r})")
            continue
        # Never cache a match we can positively identify as wrong — a silently
        # wrong club poisons the per-90 model with another squad's numbers.
        if want_country and not _same_country(tcountry, want_country):
            print(f"  [WARN] {code}: best match {tname!r} is in {tcountry!r}, "
                  f"expected {want_country!r} — NOT cached, fix SEARCH_NAMES")
            continue
        if _is_not_the_first_team(tname or ""):
            print(f"  [WARN] {code}: best match {tname!r} looks like a women's, "
                  f"youth or reserve side — NOT cached, fix SEARCH_NAMES")
            continue
        cache[code] = tid
        print(f"  {code:4s} -> {tid}  ({tname}, {tcountry})")
    json.dump(cache, open(TEAM_ID_CACHE, "w"), indent=2)
    return cache


def _add(dst: dict, block: dict) -> None:
    """Fold one competition's statistics block into a player's running totals."""
    g = block.get("games") or {}
    goals = block.get("goals") or {}
    shots = block.get("shots") or {}
    passes = block.get("passes") or {}
    tackles = block.get("tackles") or {}
    duels = block.get("duels") or {}
    cards = block.get("cards") or {}
    pen = block.get("penalty") or {}

    def n(v):
        return float(v or 0)

    dst["appearances"] += n(g.get("appearences"))
    dst["lineups"]     += n(g.get("lineups"))
    dst["minutes"]     += n(g.get("minutes"))
    dst["goals"]       += n(goals.get("total"))
    dst["assists"]     += n(goals.get("assists"))
    dst["conceded"]    += n(goals.get("conceded"))
    dst["saves"]       += n(goals.get("saves"))
    dst["shots"]       += n(shots.get("total"))
    dst["shots_on"]    += n(shots.get("on"))
    dst["key_passes"]  += n(passes.get("key"))
    dst["tackles"]     += n(tackles.get("total"))
    dst["interceptions"] += n(tackles.get("interceptions"))
    dst["duels_won"]   += n(duels.get("won"))
    dst["yellow"]      += n(cards.get("yellow"))
    dst["red"]         += n(cards.get("red"))
    dst["pens_scored"] += n(pen.get("scored"))
    dst["pens_missed"] += n(pen.get("missed"))
    dst["competitions"] += 1
    if g.get("rating"):
        try:
            dst["_rating_sum"] += float(g["rating"]) * max(n(g.get("appearences")), 1)
            dst["_rating_apps"] += max(n(g.get("appearences")), 1)
        except (TypeError, ValueError):
            pass


def fetch_club(code: str, tid: int, season: int, headers: dict) -> dict:
    out, page, total_pages = {}, 1, 1
    # One player's `statistics` array already holds every competition, so a
    # second row for the same player is a repeated page, not new data. Folding
    # it in again would silently double their minutes, so skip it.
    seen = set()
    while page <= total_pages:
        data = _get("players", {"team": tid, "season": season, "page": page}, headers)
        paging = data.get("paging") or {}
        total_pages = int(paging.get("total") or 1)
        for entry in data.get("response") or []:
            pl = entry.get("player") or {}
            name = pl.get("name") or ""
            if not name:
                continue
            key = _norm(name)
            marker = pl.get("id") or key
            if marker in seen:
                continue
            seen.add(marker)
            rec = out.setdefault(key, {
                "display_name": name, "team": code, "player_id": pl.get("id"),
                "appearances": 0.0, "lineups": 0.0, "minutes": 0.0, "goals": 0.0,
                "assists": 0.0, "conceded": 0.0, "saves": 0.0, "shots": 0.0,
                "shots_on": 0.0, "key_passes": 0.0, "tackles": 0.0,
                "interceptions": 0.0, "duels_won": 0.0, "yellow": 0.0, "red": 0.0,
                "pens_scored": 0.0, "pens_missed": 0.0, "competitions": 0,
                "_rating_sum": 0.0, "_rating_apps": 0.0,
            })
            for block in entry.get("statistics") or []:
                _add(rec, block)
        page += 1
    return out


def finalise(club: dict) -> dict:
    """Derive the fields the engine reads, and drop the running accumulators."""
    for rec in club.values():
        apps = rec.pop("_rating_apps", 0.0)
        rsum = rec.pop("_rating_sum", 0.0)
        rec["rating"] = round(rsum / apps, 2) if apps else 0.0
        # UEFA counts "ball recoveries"; tackles + interceptions is the closest
        # thing API-Football exposes.
        rec["recoveries"] = rec["tackles"] + rec["interceptions"]
    return club


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="API-Football key")
    ap.add_argument("--season", type=int, default=2025,
                    help="Season start year — 2025 means 2025/26 (default)")
    ap.add_argument("--clubs", help="Comma-separated club codes (default: all 36)")
    ap.add_argument("--refresh", action="store_true",
                    help="Re-pull clubs already saved instead of skipping them")
    ap.add_argument("--out", default=OUTPUT)
    args = ap.parse_args()

    headers = {"x-apisports-key": args.key}
    codes = ([c.strip().upper() for c in args.clubs.split(",")]
             if args.clubs else sorted(CLUBS))
    unknown = [c for c in codes if c not in CLUBS]
    if unknown:
        sys.exit(f"Unknown club code(s): {unknown}")

    # Resume: a run that dies partway (rate limit, dropped connection) has
    # already spent those requests, so re-spending them is the expensive
    # mistake. Reload what is on disk and only fetch the clubs still missing.
    all_players, per_club = {}, {}
    if os.path.exists(args.out):
        try:
            prev = json.load(open(args.out))
        except Exception as e:
            print(f"[WARN] could not read {args.out} ({e}); starting fresh")
            prev = {}
        if prev.get("season") == args.season:
            all_players = prev.get("players") or {}
            per_club = prev.get("clubs") or {}
            if per_club:
                print(f"Resuming: {len(per_club)} club(s) already saved, "
                      f"{len(all_players)} players on disk")
        elif prev:
            print(f"[WARN] {args.out} holds season {prev.get('season')}, "
                  f"not {args.season} — starting fresh")

    todo = codes if args.refresh else [c for c in codes if c not in per_club]
    if not todo:
        print("Nothing to fetch — every requested club is already saved. "
              "Use --refresh to re-pull.")
        return

    if args.refresh:
        # A re-pull usually means the club resolved to the WRONG team, so the
        # cached id and the records it produced both have to go — otherwise the
        # bad id is reused and the wrong squad's players linger in the file
        # under their own names, where nothing will ever overwrite them.
        if os.path.exists(TEAM_ID_CACHE):
            try:
                idc = json.load(open(TEAM_ID_CACHE))
                dropped = [c for c in todo if idc.pop(c, None) is not None]
                json.dump(idc, open(TEAM_ID_CACHE, "w"), indent=2)
                if dropped:
                    print(f"Dropped cached team id(s) for {dropped} — will re-resolve")
            except Exception as e:
                print(f"[WARN] could not update {TEAM_ID_CACHE}: {e}")
        stale = [k for k, v in all_players.items() if v.get("team") in set(todo)]
        for k in stale:
            del all_players[k]
        if stale:
            print(f"Cleared {len(stale)} player record(s) from {todo}")

    ids = resolve_team_ids(todo, headers)

    def save():
        json.dump({"season": args.season, "clubs": per_club,
                   "api_requests": _REQS, "players": all_players},
                  open(args.out, "w"), indent=2, ensure_ascii=False)

    print(f"\nPulling {args.season}/{str(args.season+1)[-2:]} stats "
          f"(all competitions) for {len(todo)} club(s)...")
    for i, code in enumerate(todo, 1):
        tid = ids.get(code)
        if not tid:
            print(f"  [{i:2d}/{len(todo)}] {code}: no team id, skipped")
            continue
        club = finalise(fetch_club(code, tid, args.season, headers))
        per_club[code] = len(club)
        print(f"  [{i:2d}/{len(todo)}] {code}: {len(club)} players "
              f"({_REQS} requests used)")
        for k, v in club.items():
            if k in all_players and (all_players[k].get("minutes") or 0) >= v["minutes"]:
                continue          # keep the club where they played more
            all_players[k] = v
        save()                    # after every club, so an interrupted run keeps its work

    save()
    with_mins = sum(1 for v in all_players.values() if (v.get("minutes") or 0) > 0)
    print(f"\nSaved {len(all_players)} players ({with_mins} with minutes) -> {args.out}")
    print(f"API requests used this run: {_REQS}")
    missing = [c for c in codes if c not in per_club]
    if missing:
        print(f"Still missing {len(missing)} club(s): {missing}")
        print("Re-run the same command to pick up only those.")
    print("\nNext: commit data/ucl_player_stats.json and push.")


if __name__ == "__main__":
    main()
