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

MIN_MINUTES_CLUB = 450   # ~5 full league games
MIN_MINUTES_NT   = 180   # ~2 full international games

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

# NT competitions — multiple (league, season) pairs tried in order; first with
# data wins. WCQ leagues span 2023-2025 so we try both years.
NT_COMPETITIONS = {
    "Copa América 2024":         [(9,   2024)],
    "AFCON 2025":                [(10,  2025), (10,  2024)],
    "UEFA Nations League 24-25": [(5,   2024)],
    "UEFA WCQ 2026":             [(960, 2024), (960, 2025), (960, 2023)],
    "CONMEBOL WCQ 2026":         [(29,  2024), (29,  2025), (29,  2023)],
    "AFC WCQ 2026":              [(30,  2024), (30,  2025), (30,  2023)],
    "CAF WCQ 2026":              [(6,   2024), (6,   2025)],
    "CONCACAF WCQ 2026":         [(31,  2024), (31,  2025), (31,  2023)],
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


def _parse_entry(entry: dict, min_minutes: int) -> tuple | None:
    """Parse one API-Football player entry. Returns (norm_full, norm_last, norm_team, stats) or None."""
    player     = entry.get("player", {})
    name       = player.get("name", "")
    firstname  = player.get("firstname", "")
    lastname   = player.get("lastname", "")
    if not name:
        return None

    stats_list = entry.get("statistics", [])
    if not stats_list:
        return None
    s    = stats_list[0]
    games = s.get("games", {})
    mins  = games.get("minutes") or 0
    apps  = games.get("appearences") or 0   # API typo
    team  = (s.get("team") or {}).get("name", "")

    if mins < min_minutes:
        return None

    goals   = (s.get("goals")   or {}).get("total")   or 0
    assists = (s.get("goals")   or {}).get("assists")  or 0
    sot     = (s.get("shots")   or {}).get("on")       or 0
    kp      = (s.get("passes")  or {}).get("key")      or 0
    tackles = (s.get("tackles") or {}).get("total")    or 0

    def p90(val):
        return round((val or 0) / mins * 90, 3) if mins else 0.0

    stats = {
        "goals90":      p90(goals),
        "xa90":         p90(assists),
        "sot90":        p90(sot),
        "kp90":         p90(kp),
        "tackles90":    p90(tackles),
        "mp":           apps,
        "minutes":      mins,
        "squad":        team,
        "starter_rate": round(games.get("lineups", 0) / apps, 2) if apps else 0.0,
    }

    norm_full = norm(name)
    # Use API's own lastname field for more reliable last-name matching
    norm_last = norm(lastname) if lastname else (norm_full.split()[-1] if norm_full else "")
    norm_team = norm(team)
    return norm_full, norm_last, norm_team, stats


def build_indexes(raw_players: list, min_minutes: int) -> tuple[dict, dict]:
    """
    Returns:
      by_full: {norm_full_name: stats}
      by_last: {norm_last_name: [(norm_full, norm_team, stats)]}
    """
    by_full: dict[str, dict] = {}
    by_last: dict[str, list] = defaultdict(list)

    for entry in raw_players:
        parsed = _parse_entry(entry, min_minutes)
        if not parsed:
            continue
        norm_full, norm_last, norm_team, stats = parsed
        by_full[norm_full] = stats
        if norm_last:
            by_last[norm_last].append((norm_full, norm_team, stats))

    return by_full, by_last


def match_player(wc_norm: str, wc_club_norm: str,
                 by_full: dict, by_last: dict) -> dict | None:
    """
    Three-tier matching:
    1. Exact normalised full name
    2. Last name + club name confirmation (handles "M. Salah" vs "Mohamed Salah")
    3. Last name unique across all fetched players in this league
    """
    if wc_norm in by_full:
        return by_full[wc_norm]

    parts = wc_norm.split()
    if not parts:
        return None
    last = parts[-1]
    candidates = by_last.get(last, [])

    if not candidates:
        return None

    # Try club match first
    for _, cand_team, cand_stats in candidates:
        if wc_club_norm and wc_club_norm == cand_team:
            return cand_stats

    # Unique last name across the league — safe to assume it's the same player
    if len(candidates) == 1:
        return candidates[0][2]

    return None


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club(wc_players: dict) -> dict:
    # Accumulate all league data into merged indexes
    all_by_full: dict[str, dict] = {}
    all_by_last: dict[str, list] = defaultdict(list)

    for league_name, lid in CLUB_LEAGUES.items():
        print(f"  {league_name} (league={lid}, season={CLUB_SEASON})")
        raw = fetch_league_players(lid, CLUB_SEASON)
        by_full, by_last = build_indexes(raw, MIN_MINUTES_CLUB)
        print(f"    {len(raw)} players fetched, {len(by_full)} with ≥{MIN_MINUTES_CLUB} min")
        for nk, s in by_full.items():
            s["league"] = league_name
            if nk not in all_by_full or s["minutes"] > all_by_full[nk]["minutes"]:
                all_by_full[nk] = s
        for last, entries in by_last.items():
            all_by_last[last].extend(entries)
        time.sleep(0.5)

    print(f"\n  Total: {len(all_by_full)} unique players across all leagues")
    out = {}
    exact = fallback = 0
    for nk, wcp in wc_players.items():
        wc_club_norm = norm(wcp.get("club", ""))
        s = match_player(nk, wc_club_norm, all_by_full, all_by_last)
        if s:
            entry = dict(s)
            entry["squad"] = wcp["club"] or entry.get("squad", "")
            out[nk] = entry
            if nk in all_by_full:
                exact += 1
            else:
                fallback += 1
    print(f"  Matched {len(out)}/{len(wc_players)} WC players "
          f"({exact} exact name, {fallback} last-name fallback)")
    return out


# ---------------------------------------------------------------------------
# Build NT stats
# ---------------------------------------------------------------------------

def build_nt(wc_players: dict) -> dict:
    best_mins: dict[str, int]  = {}
    all_by_full: dict[str, dict] = {}
    all_by_last: dict[str, list] = defaultdict(list)
    sources: dict[str, str] = {}

    for comp_name, season_pairs in NT_COMPETITIONS.items():
        # Try each (league, season) pair — use first that returns data
        for lid, season in season_pairs:
            print(f"  {comp_name} (league={lid}, season={season})")
            raw = fetch_league_players(lid, season)
            by_full, by_last = build_indexes(raw, MIN_MINUTES_NT)
            print(f"    {len(raw)} players fetched, {len(by_full)} with ≥{MIN_MINUTES_NT} min")
            if by_full:
                for nk, s in by_full.items():
                    if s["minutes"] > best_mins.get(nk, 0):
                        best_mins[nk] = s["minutes"]
                        sources[nk] = comp_name
                        all_by_full[nk] = s
                for last, entries in by_last.items():
                    all_by_last[last].extend(entries)
                break   # found data for this competition — don't try next season
            time.sleep(0.4)
        time.sleep(0.5)

    out = {}
    for nk, wcp in wc_players.items():
        s = match_player(nk, "", all_by_full, all_by_last)
        if s:
            entry = dict(s)
            entry["source"] = sources.get(nk, "")
            out[nk] = entry
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
