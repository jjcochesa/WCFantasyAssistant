"""
fetch_player_stats.py — run LOCALLY, commit the output.

Pulls 2025/26 club stats + recent NT competition stats from Sofascore's
public API, writes data/stats.json. The app reads that file at startup —
zero runtime API dependency.

Usage:
    python3 fetch_player_stats.py --dry-run   # preview without writing
    python3 fetch_player_stats.py             # write data/stats.json
    git add data/stats.json && git commit -m "Refresh player stats" && git push

Re-run once before GD1, once after groups for wildcard.
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

BASE = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.sofascore.com/",
    "Origin":          "https://www.sofascore.com",
}

MIN_MINUTES = 450  # ~5 full games — below this, per-90 stats are noisy

# ---------------------------------------------------------------------------
# Sofascore unique-tournament IDs
# Club leagues — verify at sofascore.com if a league returns 0 rows
# ---------------------------------------------------------------------------

CLUB_LEAGUES = {
    "Premier League":     17,
    "La Liga":            8,
    "Bundesliga":         35,
    "Serie A":            23,
    "Ligue 1":            34,
    "Saudi Pro League":   1269,
    "Eredivisie":         37,
    "Primeira Liga":      238,
    "Süper Lig":          52,
    "Scottish Prem":      547,
    "Belgian Pro League": 11,
    "MLS":                242,
    "Liga MX":            1336,
    "Série A (Brazil)":   325,
    "Primera Div (ARG)":  155,
}

# NT competitions — most recent tournaments with meaningful sample sizes.
# Copa América + Nations League give the best form signal for the WC.
NT_COMPETITIONS = {
    "Copa América 2024":          133,
    "UEFA Nations League 24-25":  1091,
    "AFCON 2025":                 1069,
    "CONMEBOL WCQ 2026":          239,
    "UEFA WCQ 2026":              840,
    "AFC WCQ 2026":               1091,   # placeholder — update if wrong
    "CAF WCQ 2026":               1068,
    "CONCACAF WCQ 2026":          1071,
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

def _get(path: str, params: dict = None) -> dict | None:
    url = f"{BASE}/{path}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        print(f"    HTTP {r.status_code}: {url}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Season discovery — auto-finds current season ID for any tournament
# ---------------------------------------------------------------------------

_season_cache: dict[int, int] = {}


def get_season_id(tid: int) -> int | None:
    if tid in _season_cache:
        return _season_cache[tid]
    data = _get(f"unique-tournament/{tid}/seasons")
    if not data:
        return None
    seasons = data.get("seasons", [])
    # Pick the season whose year contains 2025 or 2026 (current)
    for s in seasons:
        yr = str(s.get("year", ""))
        if "2025" in yr or "2026" in yr:
            _season_cache[tid] = s["id"]
            return s["id"]
    # Fallback: most recent season
    if seasons:
        _season_cache[tid] = seasons[0]["id"]
        return seasons[0]["id"]
    return None


# ---------------------------------------------------------------------------
# Fetch all player stats for one tournament/season (paginated)
# Returns list of raw stat dicts from Sofascore
# ---------------------------------------------------------------------------

def fetch_tournament_stats(tid: int, season_id: int) -> list:
    all_rows = []
    offset   = 0
    limit    = 100
    while True:
        data = _get(
            f"unique-tournament/{tid}/season/{season_id}/statistics/player",
            params={
                "limit":        limit,
                "offset":       offset,
                "order":        "-rating",
                "accumulation": "total",
            },
        )
        if not data:
            break
        rows = data.get("statistics", [])
        all_rows.extend(rows)
        # Stop when we've received fewer rows than requested (last page)
        if len(rows) < limit:
            break
        offset += limit
        time.sleep(0.4)
    return all_rows


def rows_to_per90(rows: list) -> dict:
    """Convert raw Sofascore stat rows → {norm_name: {stat: per90_value, ...}}"""
    out = {}
    for row in rows:
        player = row.get("player", {})
        name   = player.get("name") or player.get("shortName", "")
        if not name:
            continue
        mins = int(row.get("minutesPlayed") or row.get("totalMinutesPlayed") or 0)
        apps = int(row.get("appearances") or row.get("matchesPlayed") or 0)
        if mins < MIN_MINUTES:
            continue

        def p90(val):
            return round(val / mins * 90, 3) if mins > 0 else 0.0

        # Sofascore field names (try multiple aliases for resilience)
        goals  = row.get("goals")       or row.get("goalsScored") or 0
        ast    = row.get("assists")     or 0
        sot    = (row.get("onTargetScoringAttempt")
                  or row.get("shotsOnTarget")
                  or row.get("shotOnTarget") or 0)
        kp     = (row.get("keyPass")
                  or row.get("keyPasses")
                  or row.get("chancesCreated") or 0)
        tkl    = (row.get("tackles")
                  or row.get("totalTackle")
                  or row.get("tacklesWon") or 0)
        team   = (row.get("team") or {}).get("name", "")

        key = norm(name)
        out[key] = {
            "goals90":   p90(goals),
            "xa90":      p90(ast),
            "sot90":     p90(sot),
            "kp90":      p90(kp),
            "tackles90": p90(tkl),
            "mp":        apps,
            "minutes":   mins,
            "squad":     team,
        }
    return out


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club(wc_players: dict) -> dict:
    combined: dict[str, dict] = {}

    for league_name, tid in CLUB_LEAGUES.items():
        print(f"  {league_name} (tid={tid})")
        season_id = get_season_id(tid)
        if not season_id:
            print("    no season found — skipping")
            time.sleep(0.3)
            continue
        print(f"    season_id={season_id}")
        rows = fetch_tournament_stats(tid, season_id)
        stats = rows_to_per90(rows)
        print(f"    {len(stats)} players with ≥{MIN_MINUTES} min")
        # Keep entry with most minutes (handles players who transferred)
        for nk, s in stats.items():
            if nk not in combined or s["minutes"] > combined[nk]["minutes"]:
                s["league"] = league_name
                combined[nk] = s
        time.sleep(0.6)

    print(f"\n  Total club data: {len(combined)} players")
    out = {}
    for nk, wcp in wc_players.items():
        if nk in combined:
            entry = dict(combined[nk])
            entry["squad"] = wcp["club"] or entry.get("squad", "")
            entry["starter_rate"] = (
                round(entry["minutes"] / 90 * 0.85 / entry["mp"], 2)
                if entry["mp"] > 0 else 0.0
            )
            out[nk] = entry
    print(f"  Matched {len(out)}/{len(wc_players)} WC players")
    return out


# ---------------------------------------------------------------------------
# Build NT stats — best competition by minutes for each player
# ---------------------------------------------------------------------------

def build_nt(wc_players: dict) -> dict:
    best_mins: dict[str, int]  = {}
    combined:  dict[str, dict] = {}

    for comp_name, tid in NT_COMPETITIONS.items():
        print(f"  {comp_name} (tid={tid})")
        season_id = get_season_id(tid)
        if not season_id:
            print("    no season found — skipping")
            time.sleep(0.3)
            continue
        print(f"    season_id={season_id}")
        rows = fetch_tournament_stats(tid, season_id)
        stats = rows_to_per90(rows)
        print(f"    {len(stats)} players with ≥{MIN_MINUTES} min")
        for nk, s in stats.items():
            if s["minutes"] > best_mins.get(nk, 0):
                best_mins[nk] = s["minutes"]
                s["source"] = comp_name
                combined[nk] = s
        time.sleep(0.6)

    out = {}
    for nk, wcp in wc_players.items():
        if nk in combined:
            out[nk] = combined[nk]
    print(f"\n  Matched {len(out)}/{len(wc_players)} WC players")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and preview — don't write files")
    args = parser.parse_args()

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

    print("── Club stats (Sofascore) ──────────────────────────")
    club = build_club(wc_players)

    print("\n── NT stats (Sofascore) ────────────────────────────")
    nt = build_nt(wc_players)

    # Merge
    all_keys = set(club) | set(nt)
    result = {}
    for nk in all_keys:
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
        print("\n── Sample (5 players with goals90 > 0) ────────────")
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

    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing.update(result)
    OUT.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\n✓ Wrote {len(existing)} entries → {OUT}")
    print("Next: git add data/stats.json && git commit -m 'Refresh player stats' && git push")


if __name__ == "__main__":
    main()
