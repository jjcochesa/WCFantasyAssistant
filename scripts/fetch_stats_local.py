"""
fetch_stats_local.py

Run this LOCALLY (not in the cloud) — fetches 2025/26 player stats from
FotMob's public JSON API, then generates manual_stats.json and
manual_nt_stats.json.

No API key needed. No scraping. Just JSON endpoints.

Usage:
    pip install requests pandas
    python scripts/fetch_stats_local.py [--dry-run]

Works on Mac/Windows/Linux from any home or office network.
"""

import argparse
import json
import time
import unicodedata
from pathlib import Path
from collections import defaultdict

import requests

ROOT = Path(__file__).resolve().parent.parent
SQUADS_FILE = ROOT / "data" / "wc_squads.json"
OUT_CLUB    = ROOT / "data" / "manual_stats.json"
OUT_NT      = ROOT / "data" / "manual_nt_stats.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
}

# ---------------------------------------------------------------------------
# FotMob league IDs + season strings
# ---------------------------------------------------------------------------

FOTMOB_LEAGUES = {
    "Premier League":    (47,  "2025/2026"),
    "La Liga":           (87,  "2025/2026"),
    "Bundesliga":        (54,  "2025/2026"),
    "Serie A":           (55,  "2025/2026"),
    "Ligue 1":           (53,  "2025/2026"),
    "Saudi Pro League":  (955, "2025/2026"),
    "Eredivisie":        (57,  "2025/2026"),
    "Primeira Liga":     (61,  "2025/2026"),
    "Süper Lig":         (71,  "2025/2026"),
    "Scottish Prem":     (63,  "2025/2026"),
    "Belgian Pro League":(68,  "2025/2026"),
    "MLS":               (130, "2025"),
    "Liga MX":           (230, "2025/2026"),
    "Série A (Brazil)":  (268, "2025"),
    "Primera Div (ARG)": (112, "2025"),
}

# Stats we want per player (FotMob stat keys)
FOTMOB_STATS = [
    "goals_per_90_overall",
    "expected_goals_per_90_overall",
    "assists_per_90_overall",
    "expected_assists_per_90_overall",
    "shots_on_target_per_90_overall",
    "key_passes_per_90_overall",
    "tackles_won_per_90_overall",
]

STAT_FIELD_MAP = {
    "goals_per_90_overall":             "goals90",
    "expected_goals_per_90_overall":    "xg90",
    "assists_per_90_overall":           "raw_assists90",
    "expected_assists_per_90_overall":  "xa90",
    "shots_on_target_per_90_overall":   "sot90",
    "key_passes_per_90_overall":        "kp90",
    "tackles_won_per_90_overall":       "tackles90",
}


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

_SPECIAL = str.maketrans({
    'ø': 'o', 'Ø': 'O', 'ß': 'ss',
    'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
    'ş': 's', 'Ş': 'S', 'đ': 'd', 'ð': 'd',
    'æ': 'ae', 'Æ': 'AE', 'œ': 'oe', 'þ': 'th',
})

def norm(name: str) -> str:
    name = str(name).translate(_SPECIAL)
    s = unicodedata.normalize("NFKD", name)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# ---------------------------------------------------------------------------
# FotMob fetch
# ---------------------------------------------------------------------------

def fotmob_get(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
        print(f"  HTTP {r.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def fetch_league_stat(league_id: int, season: str, stat_key: str) -> dict:
    """Returns {norm_name: value} for one stat in one league."""
    url = (f"https://www.fotmob.com/api/leagueseasondeepstats"
           f"?id={league_id}&season={season}&type=players&stat={stat_key}")
    data = fotmob_get(url)
    if not data:
        return {}

    result = {}
    # FotMob response structure: data["statsData"]["playerTable"]["rows"]
    # Each row has: name, value, teamName, appearances, minutesPlayed
    rows = (data.get("statsData") or {}).get("playerTable", {}).get("rows", [])
    if not rows:
        # Try alternate structure
        rows = data.get("players", []) or data.get("rows", [])

    for row in rows:
        name = row.get("name") or row.get("playerName", "")
        val  = row.get("value") or row.get("statValue")
        if name and val is not None:
            try:
                result[norm(name)] = float(val)
            except (ValueError, TypeError):
                pass

    return result


def fetch_league_minutes(league_id: int, season: str) -> dict:
    """Returns {norm_name: {mp, minutes, squad}} for playing time data."""
    url = (f"https://www.fotmob.com/api/leagueseasondeepstats"
           f"?id={league_id}&season={season}&type=players&stat=minutes_played_overall")
    data = fotmob_get(url)
    if not data:
        return {}

    result = {}
    rows = (data.get("statsData") or {}).get("playerTable", {}).get("rows", [])
    for row in rows:
        name = row.get("name") or row.get("playerName", "")
        mins = row.get("value") or row.get("statValue", 0)
        apps = row.get("appearances") or row.get("matchesPlayed", 0)
        team = row.get("teamName", "")
        if name:
            key = norm(name)
            try:
                result[key] = {
                    "minutes": int(float(mins)),
                    "mp":      int(float(apps)),
                    "squad":   team,
                }
            except (ValueError, TypeError):
                pass
    return result


# ---------------------------------------------------------------------------
# Build club stats from FotMob
# ---------------------------------------------------------------------------

def build_club_stats_fotmob(wc_players: dict) -> dict:
    # Collect per-player data across all leagues
    # Structure: {norm_name: {stat_key: value, ...}}
    player_stats: dict[str, dict] = defaultdict(dict)
    player_meta:  dict[str, dict] = {}

    for league_name, (lid, season) in FOTMOB_LEAGUES.items():
        print(f"\n  {league_name} (id={lid}, {season})")

        # Minutes/appearances first
        mins = fetch_league_minutes(lid, season)
        for k, v in mins.items():
            v["_league"] = league_name
            # keep entry with most minutes (handles transfers)
            if k not in player_meta or v["minutes"] > player_meta[k]["minutes"]:
                player_meta[k] = v
        time.sleep(0.5)

        # Each stat
        for stat_key in FOTMOB_STATS:
            vals = fetch_league_stat(lid, season, stat_key)
            field = STAT_FIELD_MAP[stat_key]
            for k, v in vals.items():
                # Only update if this league has more minutes for this player
                existing_min = player_meta.get(k, {}).get("minutes", 0)
                current_min  = mins.get(k, {}).get("minutes", 0)
                if current_min >= existing_min or field not in player_stats[k]:
                    player_stats[k][field] = v
            time.sleep(0.3)

    print(f"\n  FotMob data collected for {len(player_stats)} players")

    out = {}
    matched = 0
    for norm_name, wcp in wc_players.items():
        stats = player_stats.get(norm_name)
        meta  = player_meta.get(norm_name)
        if not stats and not meta:
            continue

        matched += 1
        mp      = (meta or {}).get("mp", 0)
        minutes = (meta or {}).get("minutes", 0)
        starts  = int(minutes / 90 * 0.85) if minutes else 0  # estimate

        out[norm_name] = {
            "name":         wcp["name"],
            "squad":        wcp["club"] or (meta or {}).get("squad", ""),
            "league":       (meta or {}).get("_league", ""),
            "mp":           mp,
            "starts":       starts,
            "minutes":      minutes,
            "xg90":         stats.get("xg90", 0.0),
            "xa90":         stats.get("xa90") or stats.get("raw_assists90", 0.0),
            "goals90":      stats.get("goals90", 0.0),
            "sot90":        stats.get("sot90", 0.0),
            "kp90":         stats.get("kp90", 0.0),
            "tackles90":    stats.get("tackles90", 0.0),
            "starter_rate": round(starts / mp, 2) if mp > 0 else 0.0,
            "norm_name":    norm_name,
        }

    print(f"  Matched: {matched}/{len(wc_players)} WC players")
    unmatched = [v["name"] for k, v in wc_players.items() if k not in out]
    if unmatched:
        print(f"  Not found ({len(unmatched)}): {', '.join(unmatched[:10])} ...")
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wc_players = json.load(open(SQUADS_FILE))
    players = {}
    for nation_code, team_data in wc_players["teams"].items():
        for p in team_data["players"]:
            players[norm(p["name"])] = {
                "name": p["name"], "nation": nation_code,
                "club": p.get("club", ""), "position": p.get("position", "MID"),
            }
    print(f"Loaded {len(players)} WC players\n")

    print("Fetching club stats from FotMob...")
    print("(This takes ~2-3 minutes due to rate limiting)\n")
    club_stats = build_club_stats_fotmob(players)

    if args.dry_run:
        print("\n[dry-run] Sample results (first 5 with xg90 > 0):")
        shown = 0
        for k, v in club_stats.items():
            if v["xg90"] > 0 and shown < 5:
                print(f"  {v['name']}: goals90={v['goals90']} xg90={v['xg90']} "
                      f"xa90={v['xa90']} kp90={v['kp90']} sot90={v['sot90']}")
                shown += 1
        return

    existing = json.loads(OUT_CLUB.read_text()) if OUT_CLUB.exists() else {}
    existing.update(club_stats)
    OUT_CLUB.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\n✓ Wrote {len(existing)} entries → {OUT_CLUB}")


if __name__ == "__main__":
    main()
