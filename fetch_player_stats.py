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
TEAM_CACHE   = ROOT / "data" / "apif_team_ids.json"    # club name → team_id (stable)
PLAYER_CACHE = ROOT / "data" / "apif_player_ids.json"  # norm_name → player_id (matched WC players)
INDEX_CACHE  = ROOT / "data" / "apif_league_index.json" # norm_name → player_id (all ~20k league players)

BASE         = "https://v3.football.api-sports.io"
CLUB_SEASON  = 2025   # API-Football labels 2025/26 season as 2025
MIN_MINUTES_CLUB = 450
MIN_MINUTES_NT   = 180

# ---------------------------------------------------------------------------
# League IDs — used to classify stat blocks in player responses
# ---------------------------------------------------------------------------

CLUB_LEAGUES = {
    # Big 5 Europe
    "Premier League":        39,
    "La Liga":               140,
    "Bundesliga":            78,
    "Serie A":               135,
    "Ligue 1":               61,
    # Other Europe (confirmed from HTML)
    "Eredivisie":            88,
    "Primeira Liga":         94,
    "Süper Lig":             203,
    "Scottish Prem":         179,
    "Belgian Pro League":    144,
    "Austrian Bundesliga":   218,
    "Swiss Super League":    207,
    "Greek Super League":    197,
    "Croatian HNL":          210,
    "Serbian Super Liga":    286,
    "Danish Superliga":      119,
    "Norwegian Eliteserien": 103,
    "Swedish Allsvenskan":   113,
    "Czech Liga":            345,
    "Ukrainian Premier":     333,
    # Americas
    "MLS":                   253,
    "Liga MX":               262,
    "Série A (Brazil)":      71,
    "Primera Div (ARG)":     128,
    "Colombia Primera A":    239,
    # Other Europe
    "Russian Premier League":  235,
    # Middle East / Africa
    "Saudi Pro League":      307,
    "Qatar Stars League":    305,
    "Egypt Premier League":  233,
    "Morocco Botola Pro":    200,
    # Asia / Oceania
    "J1 League":             98,
    "K League 1":            292,
    "A-League (AUS)":        188,
    "China Super League":    169,
}

CLUB_LEAGUE_IDS = set(CLUB_LEAGUES.values())

# International competition league IDs — any stat block with these is NT form
NT_LEAGUE_IDS = {
    1,    # World Cup
    4,    # Euro Championship
    5,    # UEFA Nations League
    6,    # Africa Cup of Nations (AFCON)
    9,    # Copa América
    10,   # International Friendlies
    22,   # CONCACAF Gold Cup
    29,   # World Cup - Qualification Africa
    30,   # World Cup - Qualification Asia
    31,   # World Cup - Qualification CONCACAF
    32,   # World Cup - Qualification Europe
    33,   # World Cup - Qualification Oceania
    34,   # World Cup - Qualification South America
    35,   # Asian Cup - Qualification
    36,   # Africa Cup of Nations - Qualification
    37,   # World Cup - Qualification Intercontinental Play-offs
    536,  # CONCACAF Nations League
    960,  # Euro Championship - Qualification
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

_PLAYER_ALIASES = {
    "vinicius jr":                   "vinicius junior",
    "savinho":                       "savio",
    "mat ryan":                      "mathew ryan",
    "maxwell cornet":                "maxwel cornet",
    "billal brahimi":                "bilal brahimi",
    "abdessamad ezzalzouli":         "abde ezzalzouli",
    "yeremy pino":                   "yeremi pino",
    "giovanni lo celso":             "giovani lo celso",
    "ransford yeboah konigsdorfer":  "ransford konigsdorffer",
    "mohamed amine amoura":          "mohamed amoura",
    "mustafa mohammed":              "mostafa mohamed",
    "nicolas de la cruz":            "nicolas de la cruz",
    # API-Football uses abbreviated names for these players
    "cristian romero":               "c. romero",
    "marcos acuna":                  "m. acuna",
    "jose maria gimenez":            "j. gimenez",
    "dan ndoye":                     "d. ndoye",
    "angelo preciado":               "a. preciado",
    "guido rodriguez":               "g. rodriguez",
    "maxi gomez":                    "m. gomez",
}

# Club name aliases: wc_squads name (norm'd) → API-Football name (norm'd)
_TEAM_ALIASES = {
    # MLS
    "atlanta united":            "atlanta united fc",
    "seattle sounders":          "seattle sounders fc",
    "sporting kansas city":      "sporting kc",
    "new york city":             "new york city fc",
    "new york red bulls":        "ny red bulls",
    "inter miami":               "inter miami cf",
    "la galaxy":                 "la galaxy",
    "toronto fc":                "toronto fc",
    "cf montreal":               "cf montreal",
    # Brazil
    "atletico mineiro":          "atletico mineiro",
    "atletico mg":               "atletico mineiro",
    "atletico paranaense":       "atletico paranaense",
    "atletico pr":               "atletico paranaense",
    # Germany
    "borussia mgladbach":        "borussia monchengladbach",
    "borussia m gladbach":       "borussia monchengladbach",
    # Belgium
    "club brugge":               "club brugge kv",
    # Scotland
    "hearts":                    "heart of midlothian",
    # Greece
    "aek athens":                "aek athens fc",
    "panathinaikos":             "panathinaikos fc",
    "olympiakos":                "olympiakos piraeus",
    # Czech Republic
    "slavia prague":             "sk slavia prague",
    "sparta prague":             "ac sparta prague",
    # Croatia
    "dinamo zagreb":             "gnk dinamo zagreb",
    # Middle East (hyphens now stripped by norm, but keep for safety)
    "al ahly":                   "al ahly sc",
    "al hilal":                  "al hilal",
    "al nassr":                  "al nassr",
    "al ittihad":                "al ittihad",
    "al qadsiah":                "al qadsiah",
    # Japan
    "urawa red diamonds":        "urawa reds",
    "kashima antlers":           "kashima antlers",
    # Korea
    "jeonbuk":                   "jeonbuk hyundai motors",
    "ulsan":                     "ulsan hd",
    # Australia
    "western sydney wanderers":  "western sydney",
}


def norm(name: str) -> str:
    name = str(name).replace("-", " ").replace("'", "").translate(_TRANS)
    # Handle chars with no Unicode decomposition before NFKD
    name = name.replace("ø", "o").replace("Ø", "o").replace("æ", "ae").replace("Æ", "ae").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    n = " ".join(n.split())  # collapse multiple spaces
    return _PLAYER_ALIASES.get(n, n)


def norm_team(name: str) -> str:
    """Normalise a club name, applying team-specific aliases."""
    n = norm(name)
    return _TEAM_ALIASES.get(n, n)


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

    # Build name → id map from all leagues (apply team alias to API names too)
    api_teams: dict[str, int] = {}   # norm_team_name → team_id

    for league_name, lid in CLUB_LEAGUES.items():
        data = _get("teams", {"league": lid, "season": CLUB_SEASON})
        entries = (data or {}).get("response", [])
        for entry in entries:
            t = entry["team"]
            nk = norm_team(t["name"])
            api_teams[nk] = t["id"]
        print(f"  {league_name}: {len(entries)} teams")
        time.sleep(0.3)

    # Match WC squad clubs to team IDs
    unique_clubs = {p["club"] for p in wc_players.values() if p.get("club")}
    team_ids: dict[str, int] = {}
    unmatched = []

    for club in sorted(unique_clubs):
        nk = norm_team(club)
        if nk in api_teams:
            team_ids[club] = api_teams[nk]
        else:
            # Partial word match — score by number of matching long words
            words = [w for w in nk.split() if len(w) > 4]
            if words:
                scored = [
                    (sum(1 for w in words if w in api_name), api_name, tid)
                    for api_name, tid in api_teams.items()
                ]
                best_score = max(s for s, _, _ in scored)
                best = [(n, t) for s, n, t in scored if s == best_score and s > 0]
                if len(best) == 1:
                    team_ids[club] = best[0][1]
                else:
                    unmatched.append(club)
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
# Phase 2: Player IDs — scan all covered league rosters page by page.
# Builds a name→id index of ~15,000 players locally, then matches WC players
# against it. Avoids the /players?search= endpoint which requires league/team.
# Club leagues: ~856 calls. WCQ leagues (one per confederation): ~60 calls.
# ---------------------------------------------------------------------------

# One WCQ league per confederation — covers every WC-qualified player without
# double-counting. Friendlies/tournaments/other quals are redundant here.
_PHASE2_NT_LEAGUES = {29, 30, 31, 32, 33, 34}  # CAF/AFC/CONCACAF/UEFA/OFC/CONMEBOL WCQ

def build_player_ids(wc_players: dict, use_cached_index: bool = False) -> dict:
    """Build {norm_wc_name: player_id} by scanning all covered league rosters."""

    if use_cached_index and INDEX_CACHE.exists():
        print("\nPhase 2: Re-matching from saved league index (0 API calls)...")
        api_index: dict[str, int] = json.loads(INDEX_CACHE.read_text())
        print(f"  Loaded index: {len(api_index)} players")
    else:
        print("\nPhase 2: Scanning league rosters for player IDs...")
        api_index = {}

        for league_name, lid in CLUB_LEAGUES.items():
            n = _fetch_league_players(lid, CLUB_SEASON, api_index)
            print(f"  {league_name}: +{n}  (index: {len(api_index)})")
            time.sleep(0.3)

        # WCQ leagues only — one per confederation, catches players from uncovered
        # club leagues (e.g. South Africa PSL) without redundant calls
        print("  Scanning WCQ leagues for remaining coverage...")
        for lid in sorted(_PHASE2_NT_LEAGUES):
            for season in [2025, 2024]:
                _fetch_league_players(lid, season, api_index)
                time.sleep(0.3)

        INDEX_CACHE.write_text(json.dumps(api_index, indent=2, ensure_ascii=False))
        print(f"  Index: {len(api_index)} players saved → {INDEX_CACHE}")

    # Match WC players to API IDs
    player_ids: dict[str, int] = {}
    unmatched: list[str] = []

    for nk, wcp in wc_players.items():
        pid = api_index.get(nk)
        if not pid:
            pid = _fuzzy_match(nk, api_index)
        if pid:
            player_ids[nk] = pid
        else:
            unmatched.append(wcp["name"])

    pct = len(player_ids) / len(wc_players) * 100
    print(f"  Matched {len(player_ids)}/{len(wc_players)} ({pct:.0f}%)")
    if unmatched:
        print(f"  Unmatched: {', '.join(unmatched[:10])}"
              + (" ..." if len(unmatched) > 10 else ""))

    PLAYER_CACHE.write_text(json.dumps(player_ids, indent=2, ensure_ascii=False))
    print(f"  Saved → {PLAYER_CACHE}")
    return player_ids


def _fetch_league_players(league_id: int, season: int, index: dict) -> int:
    """Paginate /players?league=&season= and add all entries to index. Returns # new."""
    added = 0
    page = 1
    while True:
        data = _get("players", {"league": league_id, "season": season, "page": page})
        if not data:
            break
        resp = data.get("response", [])
        paging = data.get("paging", {})
        for entry in resp:
            p = entry.get("player") or {}
            pid = p.get("id")
            raw = p.get("name", "")
            if pid and raw:
                nk = norm(raw)
                if nk not in index:
                    index[nk] = pid
                    added += 1
        if paging.get("current", page) >= paging.get("total", 1):
            break
        page += 1
        time.sleep(0.3)
    return added


def _fuzzy_match(wc_norm: str, api_index: dict) -> int | None:
    """Try compound last name (2 words) then single, + first-initial filter."""
    parts = wc_norm.split()
    if len(parts) < 2:
        return None
    wc_initial = parts[0][0]

    for n_last in (2, 1):
        if n_last >= len(parts):
            continue
        wc_last = " ".join(parts[-n_last:])
        candidates = [
            (name, pid) for name, pid in api_index.items()
            if " ".join(name.split()[-n_last:]) == wc_last
        ]
        if not candidates:
            continue
        if len(candidates) == 1:
            return candidates[0][1]
        by_initial = [(nm, p) for nm, p in candidates
                      if nm.split() and nm.split()[0][0] == wc_initial]
        if len(by_initial) == 1:
            return by_initial[0][1]

    return None


# ---------------------------------------------------------------------------
# Phase 3: Fetch stats per player
# Club: season=2025 only (2025/26 season)
# NT: seasons 2023+2024+2025 — accumulate raw totals across ALL NT competitions
#     so per-90s reflect combined recent international minutes, not just one cup
# ---------------------------------------------------------------------------

# When a player has few 25/26 club minutes, blend in previous-season per-90s
# proportionally. At BLEND_K minutes the weight is 50/50; a full season (~2700 min)
# is ~85% current. Keeps the current club label/squad correct while damping noise.
BLEND_K = 450


def fetch_and_parse(player_id: int) -> tuple[dict | None, dict | None]:
    """Returns (club_stats, nt_stats) for a player. None if no data."""
    club_cur  = None   # best 25/26 club block (always accepted, any minutes)
    club_prev = None   # best 24/25 or 23/24 block (threshold-gated, for blending)

    # NT accumulators — sum raw counts, compute per-90 at the end
    nt_acc = {"goals": 0, "assists": 0, "sot": 0, "kp": 0, "tackles": 0,
              "minutes": 0, "apps": 0, "lineups": 0, "comps": []}

    for season in [CLUB_SEASON, 2024, 2023]:
        data = _get("players", {"id": player_id, "season": season})
        entries = (data or {}).get("response", [])
        if not entries:
            time.sleep(0.35)
            continue

        blocks = entries[0].get("statistics", [])

        for block in blocks:
            lid = (block.get("league") or {}).get("id")
            games = block.get("games") or {}
            mins  = games.get("minutes") or 0

            if lid in CLUB_LEAGUE_IDS:
                if season == CLUB_SEASON:
                    # Always accept current-season data (correct club); no minutes gate.
                    parsed = _parse_block(block, min_minutes=0)
                    if parsed and (not club_cur or parsed["minutes"] > club_cur["minutes"]):
                        parsed["league"] = next(
                            (k for k, v in CLUB_LEAGUES.items() if v == lid), str(lid)
                        )
                        club_cur = parsed
                elif season in (2024, 2023) and club_prev is None:
                    # Previous-season data for blending — threshold-gated so a
                    # 1-game cameo doesn't pollute the blend.
                    parsed = _parse_block(block, MIN_MINUTES_CLUB)
                    if parsed and (not club_prev or parsed["minutes"] > club_prev["minutes"]):
                        parsed["league"] = next(
                            (k for k, v in CLUB_LEAGUES.items() if v == lid), str(lid)
                        )
                        club_prev = parsed

            elif lid in NT_LEAGUE_IDS and mins >= MIN_MINUTES_NT:
                comp_name = (block.get("league") or {}).get("name", str(lid))
                if comp_name not in nt_acc["comps"]:
                    nt_acc["goals"]   += (block.get("goals")   or {}).get("total")   or 0
                    nt_acc["assists"] += (block.get("goals")   or {}).get("assists")  or 0
                    nt_acc["sot"]     += (block.get("shots")   or {}).get("on")       or 0
                    nt_acc["kp"]      += (block.get("passes")  or {}).get("key")      or 0
                    nt_acc["tackles"] += (block.get("tackles") or {}).get("total")    or 0
                    nt_acc["minutes"] += mins
                    nt_acc["apps"]    += games.get("appearences") or 0
                    nt_acc["lineups"] += games.get("lineups") or 0
                    nt_acc["comps"].append(comp_name)

        time.sleep(0.35)

    # Blend current + previous season club per-90s when 25/26 minutes are sparse.
    # Always keep 25/26 squad/league (current club). If zero 25/26 data, fall back
    # entirely to previous season.
    PER90_KEYS = ("goals90", "xa90", "sot90", "kp90", "tackles90")
    if club_cur is not None and club_prev is not None:
        cur_min = club_cur["minutes"]
        w_cur   = cur_min / (cur_min + BLEND_K)
        w_prev  = 1.0 - w_cur
        if w_prev > 0.05:   # only bother blending when previous adds meaningful weight
            for k in PER90_KEYS:
                club_cur[k] = round(w_cur * club_cur.get(k, 0.0) + w_prev * club_prev.get(k, 0.0), 3)
        club_stats = club_cur
    elif club_cur is not None:
        club_stats = club_cur
    else:
        club_stats = club_prev  # zero 25/26 data — use previous season entirely

    nt_stats = None
    if nt_acc["minutes"] >= MIN_MINUTES_NT:
        m = nt_acc["minutes"]
        a = nt_acc["apps"]

        def p90(v):
            return round(v / m * 90, 3)

        nt_stats = {
            "goals90":      p90(nt_acc["goals"]),
            "xa90":         p90(nt_acc["assists"]),
            "sot90":        p90(nt_acc["sot"]),
            "kp90":         p90(nt_acc["kp"]),
            "tackles90":    p90(nt_acc["tackles"]),
            "mp":           a,
            "minutes":      m,
            "starter_rate": round(nt_acc["lineups"] / a, 2) if a else 0.0,
            "source":       ", ".join(nt_acc["comps"]),
        }

    return club_stats, nt_stats


def _parse_block(block: dict, min_minutes: int = MIN_MINUTES_CLUB) -> dict | None:
    """Parse one competition stat block into per-90 stats. Returns None if < min_minutes."""
    games   = block.get("games") or {}
    mins    = games.get("minutes") or 0
    apps    = games.get("appearences") or 0
    team    = (block.get("team") or {}).get("name", "")

    if mins < min_minutes or mins == 0:
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
    parser.add_argument("--rematch",    action="store_true",
                        help="Re-run name matching against saved index — 0 API calls")
    parser.add_argument("--only-missing", action="store_true",
                        help="Phase 3 fetches ONLY players not already in stats.json (cheap top-up)")
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
        player_ids = build_player_ids(wc_players, use_cached_index=False)
    elif args.rematch:
        player_ids = build_player_ids(wc_players, use_cached_index=True)
    else:
        player_ids = json.loads(PLAYER_CACHE.read_text())
        print(f"Phase 2: Using cached player IDs ({len(player_ids)} players)")

    # --only-missing: skip players already present in stats.json so a top-up run
    # after adding new aliases costs ~2 calls per new player instead of ~1400.
    if args.only_missing and OUT.exists():
        already = json.loads(OUT.read_text())
        before = len(player_ids)
        player_ids = {nk: pid for nk, pid in player_ids.items() if nk not in already}
        print(f"[only-missing] {before - len(player_ids)} already in stats.json, "
              f"fetching {len(player_ids)} new players")

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
