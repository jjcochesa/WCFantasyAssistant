"""
fetch_player_stats.py — run LOCALLY, commit the output.

Pulls 2025/26 club stats + recent NT stats from FotMob's public JSON API,
merges them, and writes data/stats.json.

The app reads data/stats.json at startup — zero runtime API calls.
Re-run this once before GD1 and once after the group stage for wildcard.

Usage:
    pip install requests
    python fetch_player_stats.py [--dry-run]
    git add data/stats.json && git commit -m "Refresh player stats" && git push
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.fotmob.com/",
    "Origin":          "https://www.fotmob.com",
}

# ---------------------------------------------------------------------------
# FotMob league/competition IDs
# Verify any ID by visiting: https://www.fotmob.com/leagues/{id}
# ---------------------------------------------------------------------------

CLUB_LEAGUES = {
    "Premier League":     (47,  "2025/2026"),
    "La Liga":            (87,  "2025/2026"),
    "Bundesliga":         (54,  "2025/2026"),
    "Serie A":            (55,  "2025/2026"),
    "Ligue 1":            (53,  "2025/2026"),
    "Saudi Pro League":   (955, "2025/2026"),
    "Eredivisie":         (57,  "2025/2026"),
    "Primeira Liga":      (61,  "2025/2026"),
    "Süper Lig":          (71,  "2025/2026"),
    "Scottish Prem":      (63,  "2025/2026"),
    "Belgian Pro League": (68,  "2025/2026"),
    "MLS":                (130, "2025"),
    "Liga MX":            (230, "2025/2026"),
    "Série A (Brazil)":   (268, "2025"),
    "Primera Div (ARG)":  (112, "2025"),
}

# NT competitions — combined stats across all matches tell us form over the
# qualification cycle (+ Copa América / AFCON / Nations League for depth).
# "season" value for tournaments is just the year string FotMob uses.
# If a competition returns 0 rows the script skips it silently.
NT_COMPETITIONS = {
    "UEFA Nations League 24-25":  (50,  "2024/2025"),
    "Copa América 2024":          (211, "2024"),
    "AFCON 2025":                 (9,   "2025"),
    "UEFA WCQ 2026":              (77,  "2026"),
    "CONMEBOL WCQ 2026":          (242, "2026"),
    "AFC WCQ 2026":               (25,  "2026"),
    "CAF WCQ 2026":               (107, "2026"),
    "CONCACAF WCQ 2026":          (23,  "2026"),
    "OFC WCQ 2026":               (14,  "2026"),
}

# FotMob stat keys → internal field names
STAT_MAP = {
    "goals_per_90_overall":            "goals90",
    "expected_goals_per_90_overall":   "xg90",
    "assists_per_90_overall":          "xa90",       # raw assists when xAG unavailable
    "expected_assists_per_90_overall": "xag90",      # merged into xa90 below
    "shots_on_target_per_90_overall":  "sot90",
    "key_passes_per_90_overall":       "kp90",
    "tackles_won_per_90_overall":      "tackles90",
}

# ---------------------------------------------------------------------------
# Name normalisation (mirrors data_engine._norm_name but with extra chars)
# ---------------------------------------------------------------------------

_TRANS = str.maketrans({
    "ø": "o", "Ø": "O", "ß": "ss",
    "ı": "i", "İ": "I", "ğ": "g", "Ğ": "G",
    "ş": "s", "Ş": "S", "đ": "d", "ð": "d",
    "æ": "ae", "Æ": "AE", "œ": "oe", "þ": "th",
})

_ALIASES = {
    "vinicius jr":                    "vinicius junior",
    "savinho":                        "savio",
    "mat ryan":                       "mathew ryan",
    "maxwell cornet":                 "maxwel cornet",
    "billal brahimi":                 "bilal brahimi",
    "abdessamad ezzalzouli":          "abde ezzalzouli",
    "yeremy pino":                    "yeremi pino",
    "giovanni lo celso":              "giovani lo celso",
    "ransford-yeboah konigsdorfer":   "ransford konigsdorffer",
    "mohamed amine amoura":           "mohamed amoura",
    "mustafa mohammed":               "mostafa mohamed",
}


def norm(name: str) -> str:
    name = str(name).translate(_TRANS)
    s = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    return _ALIASES.get(n, n)


# ---------------------------------------------------------------------------
# FotMob fetch helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
        print(f"    HTTP {r.status_code}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def _rows(data: dict) -> list:
    """Extract player rows from FotMob leagueseasondeepstats response."""
    if not data:
        return []
    rows = (data.get("statsData") or {}).get("playerTable", {}).get("rows", [])
    if not rows:
        rows = data.get("players") or data.get("rows") or []
    return rows


def fetch_minutes(lid: int, season: str) -> dict:
    """Returns {norm_name: {minutes, mp, squad}} for a competition."""
    url = (f"https://www.fotmob.com/api/leagueseasondeepstats"
           f"?id={lid}&season={season}&type=players&stat=minutes_played_overall")
    rows = _rows(_get(url))
    out = {}
    for row in rows:
        name = row.get("name") or row.get("playerName", "")
        mins = row.get("value") or row.get("statValue") or 0
        apps = row.get("appearances") or row.get("matchesPlayed") or 0
        team = row.get("teamName", "")
        if name:
            try:
                out[norm(name)] = {
                    "minutes": int(float(mins)),
                    "mp":      int(float(apps)),
                    "squad":   team,
                }
            except (ValueError, TypeError):
                pass
    return out


def fetch_stat(lid: int, season: str, stat_key: str) -> dict:
    """Returns {norm_name: float} for one stat in one competition."""
    url = (f"https://www.fotmob.com/api/leagueseasondeepstats"
           f"?id={lid}&season={season}&type=players&stat={stat_key}")
    rows = _rows(_get(url))
    out = {}
    for row in rows:
        name = row.get("name") or row.get("playerName", "")
        val  = row.get("value") or row.get("statValue")
        if name and val is not None:
            try:
                out[norm(name)] = float(val)
            except (ValueError, TypeError):
                pass
    return out


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club(wc_players: dict) -> dict:
    # {norm_name: {field: value, ...}}
    stats: dict[str, dict] = defaultdict(dict)
    meta:  dict[str, dict] = {}

    for league_name, (lid, season) in CLUB_LEAGUES.items():
        print(f"  {league_name}")
        mins = fetch_minutes(lid, season)
        for k, v in mins.items():
            v["_league"] = league_name
            if k not in meta or v["minutes"] > meta[k]["minutes"]:
                meta[k] = v
        time.sleep(0.5)

        for fmkey, field in STAT_MAP.items():
            vals = fetch_stat(lid, season, fmkey)
            for k, v in vals.items():
                # Keep stats from the league where the player has most minutes
                cur_mins  = mins.get(k, {}).get("minutes", 0)
                best_mins = meta.get(k, {}).get("minutes", 0)
                if cur_mins >= best_mins or field not in stats[k]:
                    stats[k][field] = v
            time.sleep(0.3)

    print(f"\n  FotMob returned data for {len(stats)} players")

    out = {}
    for nk, wcp in wc_players.items():
        s = stats.get(nk)
        m = meta.get(nk)
        if not s and not m:
            continue
        mp      = (m or {}).get("mp", 0)
        minutes = (m or {}).get("minutes", 0)
        starts  = int(minutes / 90 * 0.85) if minutes else 0

        # Prefer xAG (expected assists) over raw assists when both present
        xa = s.get("xag90") or s.get("xa90", 0.0)

        out[nk] = {
            "xg90":        s.get("xg90",      0.0),
            "xa90":        xa,
            "goals90":     s.get("goals90",   0.0),
            "sot90":       s.get("sot90",     0.0),
            "kp90":        s.get("kp90",      0.0),
            "tackles90":   s.get("tackles90", 0.0),
            "mp":          mp,
            "minutes":     minutes,
            "starts":      starts,
            "starter_rate": round(starts / mp, 2) if mp else 0.0,
            "squad":       wcp["club"] or (m or {}).get("squad", ""),
            "league":      (m or {}).get("_league", ""),
        }
    return out


# ---------------------------------------------------------------------------
# Build NT stats — aggregate across all qualifying competitions, keep entry
# with highest minutes for each player (handles Copa vs WCQ depth)
# ---------------------------------------------------------------------------

def build_nt(wc_players: dict) -> dict:
    best_mins: dict[str, int]  = {}  # norm_name -> minutes at best competition
    agg:       dict[str, dict] = defaultdict(dict)
    sources:   dict[str, str]  = {}

    for comp_name, (lid, season) in NT_COMPETITIONS.items():
        print(f"  {comp_name}")
        mins = fetch_minutes(lid, season)
        if not mins:
            print("    (no data)")
            time.sleep(0.4)
            continue

        for fmkey, field in STAT_MAP.items():
            vals = fetch_stat(lid, season, fmkey)
            for k, v in vals.items():
                cur_mins  = mins.get(k, {}).get("minutes", 0)
                prev_best = best_mins.get(k, 0)
                if cur_mins > prev_best or field not in agg[k]:
                    agg[k][field] = v
            time.sleep(0.3)

        for k, m in mins.items():
            if m["minutes"] > best_mins.get(k, 0):
                best_mins[k] = m["minutes"]
                sources[k]   = comp_name
                agg[k]["mp"]      = m["mp"]
                agg[k]["minutes"] = m["minutes"]

        time.sleep(0.5)

    out = {}
    for nk, wcp in wc_players.items():
        s = agg.get(nk)
        if not s:
            continue
        xa = s.get("xag90") or s.get("xa90", 0.0)
        out[nk] = {
            "xg90":      s.get("xg90",      0.0),
            "xa90":      xa,
            "goals90":   s.get("goals90",   0.0),
            "sot90":     s.get("sot90",     0.0),
            "kp90":      s.get("kp90",      0.0),
            "tackles90": s.get("tackles90", 0.0),
            "mp":        s.get("mp",        0),
            "minutes":   s.get("minutes",   0),
            "source":    sources.get(nk, ""),
        }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch data but don't write files — just show a sample")
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

    print("── Club stats (FotMob) ─────────────────────────────")
    club = build_club(wc_players)
    print(f"  Matched {len(club)}/{len(wc_players)} players\n")

    print("── NT stats (FotMob) ───────────────────────────────")
    nt = build_nt(wc_players)
    print(f"  Matched {len(nt)}/{len(wc_players)} players\n")

    # Merge into unified output
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
        print(f"No data for {len(unmatched)} players: {', '.join(unmatched[:10])}"
              + (" ..." if len(unmatched) > 10 else ""))

    if args.dry_run:
        print("\n── Sample (5 players with xg90 > 0) ───────────────")
        shown = 0
        for nk, e in result.items():
            c = e.get("club", {})
            if c.get("xg90", 0) > 0 and shown < 5:
                n = e.get("nt", {})
                print(f"  {e['name']}")
                print(f"    club : xg90={c['xg90']:.3f} kp90={c['kp90']:.3f} "
                      f"sot90={c['sot90']:.3f} tkl90={c['tackles90']:.3f}")
                print(f"    nt   : xg90={n.get('xg90',0):.3f} kp90={n.get('kp90',0):.3f} "
                      f"src={n.get('source','—')}")
                shown += 1
        print("\n[dry-run] Nothing written.")
        return

    # Merge with any existing file (preserve hand-curated entries)
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing.update(result)
    OUT.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"✓ Wrote {len(existing)} entries → {OUT}")
    print("\nNext: git add data/stats.json && git commit -m 'Refresh player stats' && git push")


if __name__ == "__main__":
    main()
