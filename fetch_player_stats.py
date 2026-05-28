"""
fetch_player_stats.py — run LOCALLY once, commit the output.

Three-phase pipeline using API-Football:
  Phase 1: Fetch team IDs for all WC squad clubs (15 league calls)
  Phase 2: Fetch squad rosters to map player names → player IDs (~300 calls)
  Phase 3: Fetch per-player season stats for all matched WC players (~1,780 calls)

Outputs data/stats.json. The app reads that file at startup — zero runtime API
dependency. Caches team/player IDs so re-runs skip straight to Phase 3.

Usage:
    python3 fetch_player_stats.py --key YOUR_KEY --dry-run   # preview
    python3 fetch_player_stats.py --key YOUR_KEY             # write stats.json
    git add data/stats.json && git commit -m "Refresh stats" && git push

Run once before GD1, once after groups for wildcard.
"""

import argparse
import json
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import requests

ROOT       = Path(__file__).resolve().parent
SQUADS     = ROOT / "data" / "wc_squads.json"
OUT        = ROOT / "data" / "stats.json"
TEAM_CACHE = ROOT / "data" / "apif_team_ids.json"    # club name → team_id (stable)
PLAYER_CACHE = ROOT / "data" / "apif_player_ids.json" # norm_name → player_id (stable)

BASE         = "https://v3.football.api-sports.io"
CLUB_SEASON  = 2025   # API-Football labels 2025/26 season as 2025
MIN_MINUTES_CLUB = 450
MIN_MINUTES_NT   = 180

# ---------------------------------------------------------------------------
# League IDs — used to classify stat blocks in player responses
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

CLUB_LEAGUE_IDS = set(CLUB_LEAGUES.values())

# International competition league IDs — any stat block with these is NT form
NT_LEAGUE_IDS = {
    1,    # World Cup
    4,    # UEFA European Championship
    5,    # UEFA Nations League
    6,    # AFCON (Africa Cup of Nations)
    9,    # Copa América
    10,   # International Friendlies
    16,   # CONCACAF Nations League
    22,   # CONCACAF Gold Cup
    30,   # AFC WCQ
    31,   # CONCACAF WCQ
    32,   # UEFA WCQ
    34,   # CONMEBOL WCQ
    36,   # AFCON Qualification
    37,   # WCQ Playoffs (all confederations)
    29,   # CAF WCQ (Africa World Cup Qualifying)
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
# HTTP helper
# ---------------------------------------------------------------------------

_API_KEY = ""


def _get(endpoint: str, params: dict = None) -> dict | None:
    headers = {"x-apisports-key": _API_KEY}
    url = f"{BASE}/{endpoint}"
    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if data.get("errors"):
                print(f"    API error: {data['errors']}")
                return None
            return data
        print(f"    HTTP {r.status_code}: {url}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 1: Team IDs
# Fetch all teams from each covered league — ~15 API calls
# ---------------------------------------------------------------------------

def build_team_ids(wc_players: dict) -> dict:
    """Returns {club_name: team_id} for clubs in WC squads."""
    print("Phase 1: Fetching team IDs from leagues...")

    # Build name → id map from all 15 leagues
    api_teams: dict[str, int] = {}   # norm_name → team_id
    api_teams_raw: dict[str, str] = {}  # norm_name → display name

    for league_name, lid in CLUB_LEAGUES.items():
        data = _get("teams", {"league": lid, "season": CLUB_SEASON})
        entries = (data or {}).get("response", [])
        for entry in entries:
            t = entry["team"]
            nk = norm(t["name"])
            api_teams[nk] = t["id"]
            api_teams_raw[nk] = t["name"]
        print(f"  {league_name}: {len(entries)} teams")
        time.sleep(0.3)

    # Match WC squad clubs to team IDs
    unique_clubs = {p["club"] for p in wc_players.values() if p.get("club")}
    team_ids: dict[str, int] = {}
    unmatched = []

    for club in sorted(unique_clubs):
        nk = norm(club)
        if nk in api_teams:
            team_ids[club] = api_teams[nk]
        else:
            # Partial match — try if any API team name contains key words
            words = [w for w in nk.split() if len(w) > 3]
            matches = [
                (api_name, tid) for api_name, tid in api_teams.items()
                if any(w in api_name for w in words)
            ]
            if len(matches) == 1:
                team_ids[club] = matches[0][1]
            else:
                unmatched.append(club)

    print(f"\n  Matched {len(team_ids)}/{len(unique_clubs)} clubs")
    if unmatched:
        print(f"  Unmatched clubs ({len(unmatched)}): {', '.join(unmatched[:10])}"
              + (" ..." if len(unmatched) > 10 else ""))
        print("  (players from these clubs will be missing club stats)")

    TEAM_CACHE.write_text(json.dumps(team_ids, indent=2, ensure_ascii=False))
    print(f"  Saved → {TEAM_CACHE}")
    return team_ids


# ---------------------------------------------------------------------------
# Phase 2: Player IDs
# Fetch squad rosters for each matched team — ~1 call per team
# ---------------------------------------------------------------------------

def build_player_ids(wc_players: dict, team_ids: dict) -> dict:
    """Returns {norm_wc_name: player_id} by matching squad rosters."""
    print("\nPhase 2: Fetching squad rosters for player IDs...")

    # Group WC players by club
    by_club: dict[str, list] = defaultdict(list)
    for nk, wcp in wc_players.items():
        by_club[wcp.get("club", "")].append((nk, wcp))

    player_ids: dict[str, int] = {}
    unmatched = []

    for club, members in by_club.items():
        team_id = team_ids.get(club)
        if not team_id:
            unmatched.extend(wcp["name"] for _, wcp in members)
            continue

        data = _get("players/squads", {"team": team_id})
        entries = (data or {}).get("response", [])
        squad = entries[0].get("players", []) if entries else []

        # Index squad by full norm name and by last name
        sq_full: dict[str, int] = {}
        sq_last: dict[str, list] = defaultdict(list)
        for sp in squad:
            snk = norm(sp["name"])
            sq_full[snk] = sp["id"]
            last = snk.split()[-1] if snk else ""
            if last:
                sq_last[last].append((snk, sp["id"]))

        for nk, wcp in members:
            pid = _match_in_squad(nk, sq_full, sq_last)
            if pid:
                player_ids[nk] = pid
            else:
                unmatched.append(wcp["name"])

        time.sleep(0.3)

    print(f"  Matched {len(player_ids)}/{len(wc_players)} WC players to IDs")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}): {', '.join(unmatched[:8])}"
              + (" ..." if len(unmatched) > 8 else ""))

    PLAYER_CACHE.write_text(json.dumps(player_ids, indent=2, ensure_ascii=False))
    print(f"  Saved → {PLAYER_CACHE}")
    return player_ids


def _match_in_squad(wc_norm: str, sq_full: dict, sq_last: dict) -> int | None:
    """Match a WC player name against a team squad. Returns player_id or None."""
    if wc_norm in sq_full:
        return sq_full[wc_norm]

    parts = wc_norm.split()
    if not parts:
        return None
    last = parts[-1]
    candidates = sq_last.get(last, [])

    if len(candidates) == 1:
        return candidates[0][1]

    # Multiple same-last-name players: try first-name initial match
    if len(candidates) > 1 and len(parts) > 1:
        first_initial = parts[0][0]
        for snk, pid in candidates:
            if snk.startswith(first_initial):
                return pid

    return None


# ---------------------------------------------------------------------------
# Phase 3: Fetch stats per player
# Two calls per player: season=2025 (club) + season=2024 (NT qualifying)
# ---------------------------------------------------------------------------

def fetch_and_parse(player_id: int) -> tuple[dict | None, dict | None]:
    """Returns (club_stats, nt_stats) for a player. None if no data."""
    club_stats = None
    nt_stats   = None

    for season in [CLUB_SEASON, 2024]:
        data = _get("players", {"id": player_id, "season": season})
        entries = (data or {}).get("response", [])
        if not entries:
            time.sleep(0.35)
            continue

        blocks = entries[0].get("statistics", [])

        for block in blocks:
            lid = (block.get("league") or {}).get("id")

            if lid in CLUB_LEAGUE_IDS and season == CLUB_SEASON:
                parsed = _parse_block(block, MIN_MINUTES_CLUB)
                if parsed and (not club_stats or parsed["minutes"] > club_stats["minutes"]):
                    parsed["league"] = next(
                        (k for k, v in CLUB_LEAGUES.items() if v == lid), str(lid)
                    )
                    club_stats = parsed

            elif lid in NT_LEAGUE_IDS:
                parsed = _parse_block(block, MIN_MINUTES_NT)
                if parsed and (not nt_stats or parsed["minutes"] > nt_stats["minutes"]):
                    parsed["source"] = (block.get("league") or {}).get("name", str(lid))
                    nt_stats = parsed

        time.sleep(0.35)

    return club_stats, nt_stats


def _parse_block(block: dict, min_minutes: int = MIN_MINUTES_CLUB) -> dict | None:
    """Parse one competition stat block into per-90 stats. Returns None if < min_minutes."""
    games   = block.get("games") or {}
    mins    = games.get("minutes") or 0
    apps    = games.get("appearences") or 0
    team    = (block.get("team") or {}).get("name", "")

    if mins < min_minutes:
        return None

    goals   = (block.get("goals")   or {}).get("total")   or 0
    assists = (block.get("goals")   or {}).get("assists")  or 0
    sot     = (block.get("shots")   or {}).get("on")       or 0
    kp      = (block.get("passes")  or {}).get("key")      or 0
    tackles = (block.get("tackles") or {}).get("total")    or 0

    def p90(v):
        return round((v or 0) / mins * 90, 3)

    return {
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _API_KEY

    parser = argparse.ArgumentParser()
    parser.add_argument("--key",        required=True,  help="API-Football key")
    parser.add_argument("--dry-run",    action="store_true", help="Preview — don't write")
    parser.add_argument("--rebuild-ids", action="store_true",
                        help="Force re-run Phases 1+2 even if cache exists")
    parser.add_argument("--inspect",    type=int, metavar="PLAYER_ID",
                        help="Dump all raw stat blocks for a player ID (use to discover NT league IDs)")
    args = parser.parse_args()
    _API_KEY = args.key

    # Status check
    status = _get("status", {})
    if status:
        acct = status.get("response", {}).get("account", {})
        reqs = status.get("response", {}).get("requests", {})
        print(f"Account : {acct.get('firstname')} {acct.get('lastname')}")
        print(f"Requests: {reqs.get('current', '?')} used / "
              f"{reqs.get('limit_day', '?')} daily limit\n")

    # --inspect: dump all stat blocks for a player so you can discover league IDs
    if args.inspect:
        print(f"\nInspecting player ID {args.inspect}...")
        for season in [2025, 2024, 2023]:
            data = _get("players", {"id": args.inspect, "season": season})
            entries = (data or {}).get("response", [])
            if not entries:
                print(f"  season {season}: no data")
                continue
            blocks = entries[0].get("statistics", [])
            name = entries[0].get("player", {}).get("name", "?")
            print(f"\n  {name} — season {season} ({len(blocks)} blocks):")
            for b in blocks:
                lg = b.get("league") or {}
                gm = b.get("games") or {}
                print(f"    league_id={lg.get('id'):>5}  name={lg.get('name','?'):<35} "
                      f"country={lg.get('country','?'):<15} mins={gm.get('minutes') or 0}")
            time.sleep(0.4)
        return

    # Load WC squads
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

    # Phase 1 + 2: build ID caches (skip if cached and not forced)
    if args.rebuild_ids or not TEAM_CACHE.exists():
        team_ids = build_team_ids(wc_players)
    else:
        team_ids = json.loads(TEAM_CACHE.read_text())
        print(f"Phase 1: Using cached team IDs ({len(team_ids)} clubs)")

    if args.rebuild_ids or not PLAYER_CACHE.exists():
        player_ids = build_player_ids(wc_players, team_ids)
    else:
        player_ids = json.loads(PLAYER_CACHE.read_text())
        print(f"Phase 2: Using cached player IDs ({len(player_ids)} players)")

    # Phase 3: fetch stats
    print(f"\nPhase 3: Fetching stats for {len(player_ids)} players "
          f"(~{len(player_ids) * 2} API calls)...")

    result: dict[str, dict] = {}
    no_club = no_nt = 0

    for i, (nk, pid) in enumerate(player_ids.items(), 1):
        wcp = wc_players.get(nk, {})
        club_stats, nt_stats = fetch_and_parse(pid)

        if not club_stats:
            no_club += 1
        if not nt_stats:
            no_nt += 1

        if club_stats or nt_stats:
            entry: dict = {"name": wcp.get("name", nk)}
            if club_stats:
                club_stats["squad"] = wcp.get("club") or club_stats.get("squad", "")
                entry["club"] = club_stats
            if nt_stats:
                entry["nt"] = nt_stats
            result[nk] = entry

        if i % 50 == 0:
            print(f"  {i}/{len(player_ids)} done — "
                  f"{len(result)} with data, {no_club} no club, {no_nt} no NT")

    print(f"\n  Done: {len(result)} players with stats")
    print(f"  No club stats: {no_club} | No NT stats: {no_nt}")

    # Preview
    if args.dry_run:
        print("\n── Sample (5 players) ───────────────────────────────")
        shown = 0
        for nk, e in result.items():
            c = e.get("club", {})
            n = e.get("nt", {})
            if c.get("goals90", 0) > 0 and shown < 5:
                print(f"  {e['name']} ({c.get('league', '?')})")
                print(f"    club: g90={c['goals90']} a90={c['xa90']} "
                      f"sot90={c['sot90']} kp90={c['kp90']} tkl90={c['tackles90']}")
                print(f"    nt  : g90={n.get('goals90',0)} kp90={n.get('kp90',0)} "
                      f"src={n.get('source','—')}")
                shown += 1
        print("\n[dry-run] Nothing written.")
        return

    # Write output — merge with existing to preserve manual entries
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing.update(result)
    OUT.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\n✓ Wrote {len(existing)} entries → {OUT}")
    print("Next: git add data/stats.json && git commit -m 'Refresh player stats' && git push")


if __name__ == "__main__":
    main()
