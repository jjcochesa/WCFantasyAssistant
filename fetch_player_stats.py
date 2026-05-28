"""
fetch_player_stats.py — run LOCALLY once, commit the output.

Pulls 2025/26 club stats + recent NT competition stats from API-Football,
writes data/stats.json. The app reads that file at startup — zero runtime
API calls, no risk of burning your quota.

Usage:
    python3 fetch_player_stats.py --key YOUR_KEY --dry-run   # preview
    python3 fetch_player_stats.py --key YOUR_KEY             # write stats.json
    git add data/stats.json && git commit -m "Refresh player stats" && git push

Run once before GD1, once after the group stage for wildcard.
"""

import argparse
import json
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import requests

ROOT   = Path(__file__).resolve().parent
SQUADS = ROOT / "data" / "wc_squads.json"
OUT    = ROOT / "data" / "stats.json"

BASE = "https://v3.football.api-sports.io"

MIN_MINUTES = 450   # ~5 full games — below this per-90 stats are noisy

# ---------------------------------------------------------------------------
# API-Football league IDs
# Club leagues: 2025/26 season (season=2025)
# ---------------------------------------------------------------------------

CLUB_LEAGUES = {
    "Premier League":     39,
    "La Liga":            140,
    "Bundesliga":         78,
    "Serie A":            135,
    "Ligue 1":            61,
    "Saudi Pro League":   307,
    "Eredivisie":         88,
    "Primeira Liga":      94,
    "Süper Lig":          203,
    "Scottish Prem":      179,
    "Belgian Pro League": 144,
    "MLS":                253,
    "Liga MX":            262,
    "Série A (Brazil)":   71,
    "Primera Div (ARG)":  128,
}
CLUB_SEASON = 2025   # API-Football uses the year the season started

# NT competitions — covers all WC 2026 qualifying confederations + Copa/AFCON
NT_COMPETITIONS = {
    "Copa América 2024":        (9,   2024),
    "AFCON 2025":               (34,  2025),
    "UEFA Nations League 24-25":(5,   2024),
    "UEFA WCQ 2026":            (960, 2025),
    "CONMEBOL WCQ 2026":        (29,  2025),
    "AFC WCQ 2026":             (30,  2025),
    "CAF WCQ 2026":             (29,  2025),
    "CONCACAF WCQ 2026":        (31,  2025),
}

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

_TRANS = str.maketrans({
    "ø": "o", "Ø": "O", "ß": "ss",
    "ı": "i", "İ": "I", "ğ": "g", "Ğ": "G",
    "ş": "s", "Ş": "S", "đ": "d", "ð": "d",
    "æ": "ae", "Æ": "AE", "œ": "oe", "þ": "th",
})

_ALIASES = {
    "vinicius jr":                  "vinicius junior",
    "savinho":                      "savio",
    "mat ryan":                     "mathew ryan",
    "maxwell cornet":               "maxwel cornet",
    "billal brahimi":               "bilal brahimi",
    "abdessamad ezzalzouli":        "abde ezzalzouli",
    "yeremy pino":                  "yeremi pino",
    "giovanni lo celso":            "giovani lo celso",
    "ransford-yeboah konigsdorfer": "ransford konigsdorffer",
    "mohamed amine amoura":         "mohamed amoura",
    "mustafa mohammed":             "mostafa mohamed",
}


def norm(name: str) -> str:
    name = str(name).translate(_TRANS)
    s = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    return _ALIASES.get(n, n)


# ---------------------------------------------------------------------------
# HTTP — single helper, all requests go through here
# ---------------------------------------------------------------------------

_API_KEY = ""


def _get(endpoint: str, params: dict) -> dict | None:
    headers = {"x-apisports-key": _API_KEY}
    url = f"{BASE}/{endpoint}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        remaining = r.headers.get("x-ratelimit-requests-remaining", "?")
        if r.status_code == 200:
            data = r.json()
            errors = data.get("errors", {})
            if errors:
                print(f"    API error: {errors}")
                return None
            return data
        print(f"    HTTP {r.status_code} (remaining: {remaining})")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Fetch all pages for a league/season
# Returns list of raw player stat objects from API-Football
# ---------------------------------------------------------------------------

def fetch_league_players(league_id: int, season: int) -> list:
    all_players = []
    page = 1
    while True:
        data = _get("players", {"league": league_id, "season": season, "page": page})
        if not data:
            break
        results = data.get("response", [])
        all_players.extend(results)
        paging = data.get("paging", {})
        if page >= paging.get("total", 1):
            break
        page += 1
        time.sleep(0.35)   # stay well under rate limit
    return all_players


def parse_to_per90(raw_players: list, squad_override: str = "") -> dict:
    """Convert API-Football player responses → {norm_name: stats_dict}."""
    out = {}
    for entry in raw_players:
        player = entry.get("player", {})
        name   = player.get("name", "")
        if not name:
            continue

        # API-Football returns one stat block per team per season
        stats_list = entry.get("statistics", [])
        if not stats_list:
            continue
        s = stats_list[0]   # take first (most recent) team

        games  = s.get("games", {})
        mins   = games.get("minutes") or 0
        apps   = games.get("appearences") or 0   # API typo: "appearences"
        team   = (s.get("team") or {}).get("name", "")

        if (mins or 0) < MIN_MINUTES:
            continue

        goals  = (s.get("goals") or {}).get("total") or 0
        assists= (s.get("goals") or {}).get("assists") or 0
        shots  = s.get("shots") or {}
        sot    = shots.get("on") or 0
        passes = s.get("passes") or {}
        kp     = passes.get("key") or 0
        tackles= (s.get("tackles") or {}).get("total") or 0

        def p90(val):
            return round((val or 0) / mins * 90, 3) if mins else 0.0

        key = norm(name)
        out[key] = {
            "goals90":     p90(goals),
            "xa90":        p90(assists),
            "sot90":       p90(sot),
            "kp90":        p90(kp),
            "tackles90":   p90(tackles),
            "mp":          apps,
            "minutes":     mins,
            "squad":       squad_override or team,
            "starter_rate": round(games.get("lineups", 0) / apps, 2) if apps else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club(wc_players: dict) -> dict:
    combined: dict[str, dict] = {}

    for league_name, lid in CLUB_LEAGUES.items():
        print(f"  {league_name} (league={lid}, season={CLUB_SEASON})")
        raw = fetch_league_players(lid, CLUB_SEASON)
        stats = parse_to_per90(raw)
        print(f"    {len(raw)} players fetched, {len(stats)} with ≥{MIN_MINUTES} min")
        for nk, s in stats.items():
            if nk not in combined or s["minutes"] > combined[nk]["minutes"]:
                s["league"] = league_name
                combined[nk] = s
        time.sleep(0.5)

    print(f"\n  Total: {len(combined)} players with club data")
    out = {}
    for nk, wcp in wc_players.items():
        if nk in combined:
            entry = dict(combined[nk])
            entry["squad"] = wcp["club"] or entry.get("squad", "")
            out[nk] = entry
    print(f"  Matched {len(out)}/{len(wc_players)} WC players")
    return out


# ---------------------------------------------------------------------------
# Build NT stats
# ---------------------------------------------------------------------------

def build_nt(wc_players: dict) -> dict:
    best_mins: dict[str, int]  = {}
    combined:  dict[str, dict] = {}

    for comp_name, (lid, season) in NT_COMPETITIONS.items():
        print(f"  {comp_name} (league={lid}, season={season})")
        raw = fetch_league_players(lid, season)
        stats = parse_to_per90(raw)
        print(f"    {len(raw)} players fetched, {len(stats)} with ≥{MIN_MINUTES} min")
        for nk, s in stats.items():
            if s["minutes"] > best_mins.get(nk, 0):
                best_mins[nk] = s["minutes"]
                s["source"] = comp_name
                combined[nk] = s
        time.sleep(0.5)

    out = {}
    for nk in wc_players:
        if nk in combined:
            out[nk] = combined[nk]
    print(f"\n  Matched {len(out)}/{len(wc_players)} WC players")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _API_KEY

    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="API-Football key")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and preview — don't write files")
    parser.add_argument("--nt-only", action="store_true",
                        help="Only fetch NT stats (skip club leagues)")
    parser.add_argument("--club-only", action="store_true",
                        help="Only fetch club stats")
    args = parser.parse_args()
    _API_KEY = args.key

    # Quick quota check
    status = _get("status", {})
    if status:
        acct = status.get("response", {}).get("account", {})
        reqs = status.get("response", {}).get("requests", {})
        print(f"Account: {acct.get('firstname')} {acct.get('lastname')}")
        print(f"Requests today: {reqs.get('current', '?')} / {reqs.get('limit_day', '?')}\n")

    raw = json.loads(SQUADS.read_text())
    wc_players: dict[str, dict] = {}
    for nation, team in raw["teams"].items():
        for p in team["players"]:
            wc_players[norm(p["name"])] = {
                "name":     p["name"],
                "nation":   nation,
                "club":     p.get("club", ""),
                "position": p.get("position", "MID"),
            }
    print(f"Loaded {len(wc_players)} WC squad players\n")

    club, nt = {}, {}

    if not args.nt_only:
        print("── Club stats (API-Football) ────────────────────────")
        club = build_club(wc_players)

    if not args.club_only:
        print("\n── NT stats (API-Football) ──────────────────────────")
        nt = build_nt(wc_players)

    # Merge
    result = {}
    for nk in set(club) | set(nt):
        wcp = wc_players.get(nk, {})
        entry: dict = {"name": wcp.get("name", nk)}
        if nk in club:
            entry["club"] = club[nk]
        if nk in nt:
            entry["nt"] = nt[nk]
        result[nk] = entry

    unmatched = [v["name"] for k, v in wc_players.items() if k not in result]
    if unmatched:
        print(f"\nNo data for {len(unmatched)} players: "
              + ", ".join(unmatched[:10])
              + (" ..." if len(unmatched) > 10 else ""))

    if args.dry_run:
        print("\n── Sample (5 players with goals90 > 0) ─────────────")
        shown = 0
        for nk, e in result.items():
            c = e.get("club", {})
            if c.get("goals90", 0) > 0 and shown < 5:
                n = e.get("nt", {})
                print(f"  {e['name']}")
                print(f"    club: goals90={c['goals90']} xa90={c['xa90']} "
                      f"sot90={c['sot90']} kp90={c['kp90']} tkl90={c['tackles90']}")
                print(f"    nt:   goals90={n.get('goals90',0)} kp90={n.get('kp90',0)} "
                      f"src={n.get('source','—')}")
                shown += 1
        print("\n[dry-run] Nothing written.")
        return

    # Merge with existing (preserves manually curated entries)
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing.update(result)
    OUT.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\n✓ Wrote {len(existing)} entries → {OUT}")
    print("Next: git add data/stats.json && git commit -m 'Refresh player stats' && git push")


if __name__ == "__main__":
    main()
