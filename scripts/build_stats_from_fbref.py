"""
build_stats_from_fbref.py

Reads FBref HTML page saves from data/fbref/ and writes:
  data/manual_stats.json      (2025/26 club stats)
  data/manual_nt_stats.json   (WC 2026 qualifying NT stats)

HOW TO SAVE PAGES:
  1. Open URL in browser
  2. Cmd+S / Ctrl+S  →  choose "Page Source" (Mac/Safari) or "Webpage, HTML Only"
  3. Save into data/fbref/ with exact filename from FBREF_DOWNLOAD_GUIDE.md

Usage:
    pip install pandas lxml beautifulsoup4
    python scripts/build_stats_from_fbref.py [--dry-run]
"""

import argparse
import json
import unicodedata
from pathlib import Path
from collections import defaultdict

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FBREF_DIR = ROOT / "data" / "fbref"
SQUADS_FILE = ROOT / "data" / "wc_squads.json"
OUT_CLUB = ROOT / "data" / "manual_stats.json"
OUT_NT = ROOT / "data" / "manual_nt_stats.json"

# ---------------------------------------------------------------------------
# FBref data-stat keys we extract from each table type
#
# Standard stats page columns (data-stat keys):
#   player, team, games, games_starts, minutes, minutes_90s
#   goals, assists, goals_per90, assists_per90
#   xg (if present), xg_assist (if present), npxg (if present)
#
# Shooting stats page columns (data-stat keys):
#   player, shots_on_target_per90, shots_per90, npxg, npxg_per90 (if present)
# ---------------------------------------------------------------------------

CLUB_FILES = {
    # Big 5 combined — has goals_per90, assists_per90, minutes (no xG)
    "Big5_standard":         ("Big 5 European Leagues", "standard"),
    "Big5_shooting":         ("Big 5 European Leagues", "shooting"),

    # Individual leagues (richer columns, include xG if FBref provides it)
    "club_PL_standard":      ("Premier League",  "standard"),
    "club_PL_shooting":      ("Premier League",  "shooting"),
    "club_LaLiga_standard":  ("La Liga",         "standard"),
    "club_LaLiga_shooting":  ("La Liga",         "shooting"),
    "club_Bundesliga_standard": ("Bundesliga",   "standard"),
    "club_Bundesliga_shooting": ("Bundesliga",   "shooting"),
    "club_SerieA_standard":  ("Serie A",         "standard"),
    "club_SerieA_shooting":  ("Serie A",         "shooting"),
    "club_Ligue1_standard":  ("Ligue 1",         "standard"),
    "club_Ligue1_shooting":  ("Ligue 1",         "shooting"),
    "club_Saudi_standard":   ("Saudi Pro League","standard"),
    "club_Saudi_shooting":   ("Saudi Pro League","shooting"),
    "club_Eredivisie_standard":  ("Eredivisie",  "standard"),
    "club_Eredivisie_shooting":  ("Eredivisie",  "shooting"),
    "club_PrimeiraLiga_standard":("Primeira Liga","standard"),
    "club_PrimeiraLiga_shooting":("Primeira Liga","shooting"),
    "club_SuperLig_standard":    ("Süper Lig",   "standard"),
    "club_SuperLig_shooting":    ("Süper Lig",   "shooting"),
    "club_Scottish_standard":    ("Scottish Prem","standard"),
    "club_Scottish_shooting":    ("Scottish Prem","shooting"),
    "club_Belgian_standard":     ("Belgian Pro League","standard"),
    "club_Belgian_shooting":     ("Belgian Pro League","shooting"),
    "club_MLS_standard":     ("MLS",             "standard"),
    "club_MLS_shooting":     ("MLS",             "shooting"),
    "club_LigaMX_standard":  ("Liga MX",         "standard"),
    "club_LigaMX_shooting":  ("Liga MX",         "shooting"),
    "club_BrazilA_standard": ("Série A Brazil",  "standard"),
    "club_BrazilA_shooting": ("Série A Brazil",  "shooting"),
    "club_Argentina_standard":("Primera Div ARG","standard"),
    "club_Argentina_shooting":("Primera Div ARG","shooting"),
}

NT_FILES = {
    "nt_UEFA_WC":          ("UEFA WC 2026 Qualifying",    "standard"),
    "nt_CONMEBOL_WC":      ("CONMEBOL WC 2026 Qualifying","standard"),
    "nt_CAF_WC":           ("CAF WC 2026 Qualifying",     "standard"),
    "nt_CONCACAF_WC":      ("CONCACAF WC 2026 Qualifying","standard"),
    "nt_AFC_WC":           ("AFC WC 2026 Qualifying",     "standard"),
    "nt_AFCON2025":        ("AFCON 2025",                 "standard"),
    "nt_CopaAmerica2024":  ("Copa América 2024",          "standard"),
    "nt_UEFANationsLeague":("UEFA Nations League 24-25",  "standard"),
}

CLUB_ALIASES = {
    "man utd": "manchester utd", "man city": "manchester city",
    "nottm forest": "nott'ham forest", "ac milan": "milan",
    "borussia dortmund": "dortmund", "borussia m'gladbach": "m'gladbach",
    "atletico madrid": "atlético madrid", "athletic bilbao": "athletic club",
    "psg": "paris s-g", "inter milan": "inter",
    "rb leipzig": "rb leipzig", "leipzig": "rb leipzig",
    "bayer leverkusen": "leverkusen", "la galaxy": "la galaxy",
    "lafc": "los angeles fc",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()

def norm_club(name: str) -> str:
    n = norm(name)
    return CLUB_ALIASES.get(n, n)

def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(str(val).replace(",", "").strip())
        return f if pd.notna(f) else default
    except (ValueError, TypeError):
        return default

def per90(total: float, nineties: float) -> float:
    return round(total / nineties, 3) if nineties > 0 else 0.0

def load_squads() -> dict:
    sq = json.load(open(SQUADS_FILE))
    players = {}
    for nation_code, team_data in sq["teams"].items():
        for p in team_data["players"]:
            key = norm(p["name"])
            players[key] = {
                "name": p["name"], "nation": nation_code,
                "club": p.get("club", ""), "position": p.get("position", "MID"),
            }
    return players

def find_file(stem: str) -> Path | None:
    for ext in (".html", ".htm", ".csv"):
        p = FBREF_DIR / (stem + ext)
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Core parser — reads FBref HTML using data-stat attributes
# This is much more reliable than column name matching because FBref's
# data-stat keys are stable even when display names change
# ---------------------------------------------------------------------------

def parse_fbref_html(path: Path, file_type: str) -> dict:
    """
    Parse a saved FBref page. Returns {norm_player_name: stats_dict}.
    Uses data-stat attributes from the HTML for reliable column mapping.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    # Find the right table
    table_ids = (["stats_shooting", "stats_shooting_expanded"]
                 if file_type == "shooting"
                 else ["stats_standard", "stats_standard_expanded",
                       "stats_keeper", "stats_keeper_expanded"])

    table = None
    for tid in table_ids:
        table = soup.find("table", id=tid)
        if table:
            break
    if table is None:
        # fallback: any large table with a player column
        for t in soup.find_all("table"):
            if t.find("td", {"data-stat": "player"}):
                table = t
                break
    if table is None:
        print(f"    ✗ No suitable table in {path.name}")
        return {}

    result = {}
    tbody = table.find("tbody")
    if tbody is None:
        return {}

    for tr in tbody.find_all("tr"):
        # Skip section header rows
        if tr.get("class") and "thead" in " ".join(tr.get("class", [])):
            continue

        def cell(stat):
            td = tr.find(["td", "th"], {"data-stat": stat})
            return td.get_text(strip=True) if td else ""

        pname = cell("player")
        if not pname or pname == "Player":
            continue
        key = norm(pname)
        squad = norm_club(cell("team"))

        if file_type == "shooting":
            # shooting page: shots on target per90, total xG (npxg)
            sot90   = safe_float(cell("shots_on_target_per90"))
            sh90    = safe_float(cell("shots_per90"))
            npxg    = safe_float(cell("npxg"))          # total npxG
            npxg90  = safe_float(cell("npxg_per90") or cell("npxg_per_shot"))
            minutes_90s = safe_float(cell("minutes_90s"))

            # derive npxg per 90 if not directly available
            if npxg90 == 0 and npxg > 0 and minutes_90s > 0:
                npxg90 = per90(npxg, minutes_90s)

            result[key] = {
                "_squad": squad,
                "sot90":  round(sot90, 3),
                "sh90":   round(sh90, 3),
                "xg90":   round(npxg90, 3),   # npxG is our xG proxy from shooting
            }

        else:
            # standard page
            minutes_90s = safe_float(cell("minutes_90s"))
            minutes     = safe_float(cell("minutes"))
            mp          = safe_float(cell("games"))
            starts      = safe_float(cell("games_starts"))

            # per-90 values — prefer direct per90 columns, fall back to totals
            goals90  = safe_float(cell("goals_per90"))
            assists90 = safe_float(cell("assists_per90"))

            if goals90 == 0:
                goals = safe_float(cell("goals"))
                goals90 = per90(goals, minutes_90s)
            if assists90 == 0:
                assists = safe_float(cell("assists"))
                assists90 = per90(assists, minutes_90s)

            # xG — might not exist on all pages
            xg90  = safe_float(cell("xg_per90") or cell("xg"))
            xag90 = safe_float(cell("xg_assist_per90") or cell("xg_assist"))
            if xg90 > 5:   # it's a total, not per90 — convert
                xg90 = per90(xg90, minutes_90s)
            if xag90 > 5:
                xag90 = per90(xag90, minutes_90s)

            if minutes_90s <= 0 and minutes > 0:
                minutes_90s = minutes / 90
            if minutes_90s <= 0:
                continue

            result[key] = {
                "_squad":    squad,
                "_nineties": minutes_90s,
                "mp":        int(mp),
                "starts":    int(starts),
                "minutes":   int(minutes) if minutes > 0 else int(minutes_90s * 90),
                "goals90":   round(goals90, 3),
                "xa90":      round(assists90, 3),
                "xg90":      round(xg90, 3),
                "xag90":     round(xag90, 3),
                "starter_rate": round(starts / mp, 2) if mp > 0 else 0.0,
            }

    return result


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club_stats(wc_players: dict) -> dict:
    standard_data: dict[str, dict] = {}
    shooting_data: dict[str, dict] = {}

    for stem, (league, file_type) in CLUB_FILES.items():
        path = find_file(stem)
        if not path:
            continue
        parsed = parse_fbref_html(path, file_type)
        print(f"  {path.name}: {len(parsed)} players ({league})")

        if file_type == "shooting":
            # shooting data adds sot90 and possibly xg90
            for k, v in parsed.items():
                existing = shooting_data.get(k, {})
                # keep entry with higher sot90 (more complete data)
                if v.get("sot90", 0) >= existing.get("sot90", 0):
                    shooting_data[k] = v
        else:
            for k, v in parsed.items():
                existing = standard_data.get(k)
                if existing is None or v["minutes"] > existing["minutes"]:
                    v["_league"] = league
                    standard_data[k] = v

    print(f"\nStandard data: {len(standard_data)} players")
    print(f"Shooting data: {len(shooting_data)} players")

    out = {}
    for norm_name, wcp in wc_players.items():
        std = standard_data.get(norm_name)
        if not std:
            continue
        sht = shooting_data.get(norm_name, {})

        # xg90: prefer shooting page npxG, fall back to standard page xg
        xg90 = sht.get("xg90") or std.get("xg90", 0.0)
        # xa90: assists per 90 from standard page
        xa90 = std.get("xa90", 0.0)

        out[norm_name] = {
            "name":         wcp["name"],
            "squad":        wcp["club"],
            "league":       std.get("_league", ""),
            "mp":           std["mp"],
            "starts":       std["starts"],
            "minutes":      std["minutes"],
            "xg90":         xg90,
            "xa90":         xa90,
            "goals90":      std["goals90"],
            "sot90":        sht.get("sot90", 0.0),
            "starter_rate": std["starter_rate"],
            "norm_name":    norm_name,
        }

    matched = len(out)
    unmatched = [wcp["name"] for nn, wcp in wc_players.items() if nn not in out]
    print(f"Matched: {matched}/{len(wc_players)} WC players")
    if unmatched:
        print(f"Not found ({len(unmatched)}): {', '.join(unmatched[:15])}"
              + (" ..." if len(unmatched) > 15 else ""))
    return out


# ---------------------------------------------------------------------------
# Build NT stats
# ---------------------------------------------------------------------------

def build_nt_stats(wc_players: dict) -> dict:
    nt_raw: dict[str, list] = defaultdict(list)

    for stem, (comp, file_type) in NT_FILES.items():
        path = find_file(stem)
        if not path:
            continue
        parsed = parse_fbref_html(path, file_type)
        print(f"  {path.name}: {len(parsed)} players ({comp})")
        for k, v in parsed.items():
            v["_comp"] = comp
            nt_raw[k].append(v)

    out = {}
    for norm_name, wcp in wc_players.items():
        rows = nt_raw.get(norm_name)
        if not rows:
            continue

        total_min = sum(r["minutes"] for r in rows) or 1
        def wavg(field):
            return round(sum(r.get(field, 0) * r["minutes"] for r in rows) / total_min, 3)

        total_mp    = sum(r["mp"] for r in rows)
        total_start = sum(r["starts"] for r in rows)

        out[norm_name] = {
            "name":         wcp["name"],
            "nation":       wcp["nation"],
            "pos":          wcp["position"],
            "mp":           total_mp,
            "starter_rate": round(total_start / total_mp, 2) if total_mp else 0,
            "xg90":         wavg("xg90"),
            "xa90":         wavg("xa90"),
            "goals90":      wavg("goals90"),
            "sot90":        wavg("sot90"),
            "tackles90":    0.0,
        }

    print(f"Matched: {len(out)}/{len(wc_players)} WC players to NT stats")
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    FBREF_DIR.mkdir(parents=True, exist_ok=True)
    data_files = [f for f in FBREF_DIR.glob("*") if f.suffix in (".html", ".htm", ".csv")]

    if not data_files:
        print(f"No files found in {FBREF_DIR}")
        print("See FBREF_DOWNLOAD_GUIDE.md for instructions.")
        return

    print(f"Found {len(data_files)} file(s) in {FBREF_DIR}\n")
    wc_players = load_squads()
    print(f"Loaded {len(wc_players)} WC players\n")

    print("=== Club stats ===")
    club_stats = build_club_stats(wc_players)

    print("\n=== NT stats ===")
    nt_stats = build_nt_stats(wc_players)

    if args.dry_run:
        print(f"\n[dry-run] {len(club_stats)} club entries, {len(nt_stats)} NT entries")
        print("\nSample club stats (first 5 with non-zero goals):")
        shown = 0
        for k, v in club_stats.items():
            if v["goals90"] > 0 and shown < 5:
                print(f"  {v['name']}: goals90={v['goals90']} xa90={v['xa90']} "
                      f"xg90={v['xg90']} sot90={v['sot90']}")
                shown += 1
        return

    existing_club = json.loads(OUT_CLUB.read_text()) if OUT_CLUB.exists() else {}
    existing_nt   = json.loads(OUT_NT.read_text()) if OUT_NT.exists() else {}
    existing_club.update(club_stats)
    existing_nt.update(nt_stats)

    OUT_CLUB.write_text(json.dumps(existing_club, indent=2, ensure_ascii=False))
    OUT_NT.write_text(json.dumps(existing_nt, indent=2, ensure_ascii=False))

    print(f"\n✓ {OUT_CLUB} — {len(existing_club)} entries")
    print(f"✓ {OUT_NT} — {len(existing_nt)} entries")


if __name__ == "__main__":
    main()
