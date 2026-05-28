"""
build_stats_from_fbref.py

Reads FBref HTML page saves (or CSV exports) from data/fbref/ and writes:
  data/manual_stats.json      (2025/26 club stats)
  data/manual_nt_stats.json   (WC 2026 qualifying NT stats)

HOW TO SAVE PAGES FROM FBREF:
  1. Open the FBref URL in your browser
  2. Press Ctrl+S (Windows) or Cmd+S (Mac)
  3. Choose "Webpage, HTML Only" format
  4. Save into data/fbref/ with the filename shown in FBREF_DOWNLOAD_GUIDE.md

Also accepts CSV exports if you can find the Share & Export button on FBref.

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

ROOT = Path(__file__).resolve().parent.parent
FBREF_DIR = ROOT / "data" / "fbref"
SQUADS_FILE = ROOT / "data" / "wc_squads.json"
OUT_CLUB = ROOT / "data" / "manual_stats.json"
OUT_NT = ROOT / "data" / "manual_nt_stats.json"

# ---------------------------------------------------------------------------
# File registry: filename → (league_name, file_type)
# file_type: "standard", "shooting", "nt_standard"
# Accepts both .html and .csv extensions
# ---------------------------------------------------------------------------

CLUB_FILES = {
    # Big 5 combined (one file covers PL + LaLiga + Bundesliga + Serie A + Ligue 1)
    "Big5_standard":      ("Big 5 European Leagues", "standard"),
    "Big5_shooting":      ("Big 5 European Leagues", "shooting"),

    # Individual leagues (only needed if Big5 file not present)
    "club_PL_standard":      ("Premier League",    "standard"),
    "club_PL_shooting":      ("Premier League",    "shooting"),
    "club_LaLiga_standard":  ("La Liga",           "standard"),
    "club_LaLiga_shooting":  ("La Liga",           "shooting"),
    "club_Bundesliga_standard": ("Bundesliga",     "standard"),
    "club_Bundesliga_shooting": ("Bundesliga",     "shooting"),
    "club_SerieA_standard":  ("Serie A",           "standard"),
    "club_SerieA_shooting":  ("Serie A",           "shooting"),
    "club_Ligue1_standard":  ("Ligue 1",           "standard"),
    "club_Ligue1_shooting":  ("Ligue 1",           "shooting"),

    # Other leagues
    "club_Saudi_standard":      ("Saudi Pro League",    "standard"),
    "club_Saudi_shooting":      ("Saudi Pro League",    "shooting"),
    "club_Eredivisie_standard":  ("Eredivisie",         "standard"),
    "club_Eredivisie_shooting":  ("Eredivisie",         "shooting"),
    "club_PrimeiraLiga_standard":("Primeira Liga",      "standard"),
    "club_PrimeiraLiga_shooting":("Primeira Liga",      "shooting"),
    "club_SuperLig_standard":   ("Süper Lig",           "standard"),
    "club_SuperLig_shooting":   ("Süper Lig",           "shooting"),
    "club_Scottish_standard":   ("Scottish Prem",       "standard"),
    "club_Scottish_shooting":   ("Scottish Prem",       "shooting"),
    "club_Belgian_standard":    ("Belgian Pro League",  "standard"),
    "club_Belgian_shooting":    ("Belgian Pro League",  "shooting"),
    "club_MLS_standard":        ("MLS",                 "standard"),
    "club_MLS_shooting":        ("MLS",                 "shooting"),
    "club_LigaMX_standard":     ("Liga MX",             "standard"),
    "club_LigaMX_shooting":     ("Liga MX",             "shooting"),
    "club_BrazilA_standard":    ("Série A Brazil",      "standard"),
    "club_BrazilA_shooting":    ("Série A Brazil",      "shooting"),
    "club_Argentina_standard":  ("Primera Div ARG",     "standard"),
    "club_Argentina_shooting":  ("Primera Div ARG",     "shooting"),
}

NT_FILES = {
    "nt_UEFA_WC":          ("UEFA WC 2026 Qualifying",    "nt_standard"),
    "nt_CONMEBOL_WC":      ("CONMEBOL WC 2026 Qualifying","nt_standard"),
    "nt_CAF_WC":           ("CAF WC 2026 Qualifying",     "nt_standard"),
    "nt_CONCACAF_WC":      ("CONCACAF WC 2026 Qualifying","nt_standard"),
    "nt_AFC_WC":           ("AFC WC 2026 Qualifying",     "nt_standard"),
    "nt_AFCON2025":        ("AFCON 2025",                 "nt_standard"),
    "nt_CopaAmerica2024":  ("Copa América 2024",          "nt_standard"),
    "nt_UEFANationsLeague":("UEFA Nations League 24-25",  "nt_standard"),
}

# FBref table IDs we look for in HTML files
STANDARD_TABLE_IDS = ["stats_standard", "stats_standard_expanded"]
SHOOTING_TABLE_IDS = ["stats_shooting", "stats_shooting_expanded"]

# Club name normalisation aliases (our names → FBref names)
CLUB_ALIASES = {
    "man utd":          "manchester utd",
    "man city":         "manchester city",
    "nottm forest":     "nott'ham forest",
    "ac milan":         "milan",
    "borussia dortmund":"dortmund",
    "borussia m'gladbach": "m'gladbach",
    "atletico madrid":  "atlético madrid",
    "athletic bilbao":  "athletic club",
    "psg":              "paris s-g",
    "inter milan":      "inter",
    "rb leipzig":       "rb leipzig",
    "leipzig":          "rb leipzig",
    "bayer leverkusen": "leverkusen",
    "la galaxy":        "la galaxy",
    "lafc":             "los angeles fc",
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
        f = float(str(val).replace(",", ""))
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
                "name":     p["name"],
                "nation":   nation_code,
                "club":     p.get("club", ""),
                "position": p.get("position", "MID"),
            }
    return players


# ---------------------------------------------------------------------------
# File reading — handles both HTML saves and CSV exports
# ---------------------------------------------------------------------------

def find_file(stem: str) -> Path | None:
    """Find data/fbref/<stem>.html or <stem>.csv, html preferred."""
    for ext in (".html", ".htm", ".csv"):
        p = FBREF_DIR / (stem + ext)
        if p.exists():
            return p
    return None


def read_table_from_html(path: Path, table_ids: list[str]) -> pd.DataFrame | None:
    """Extract a specific table from a saved FBref HTML page."""
    try:
        tables = pd.read_html(str(path), attrs={"id": tid} if (tid := next(
            (t for t in table_ids), None)) else None)
    except Exception:
        tables = []

    # Try each table id until one works
    for tid in table_ids:
        try:
            dfs = pd.read_html(str(path), attrs={"id": tid})
            if dfs:
                df = dfs[0]
                # FBref uses MultiIndex columns — flatten them
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [
                        col[-1] if col[-1] != col[0] else col[0]
                        for col in df.columns
                    ]
                return _clean_df(df)
        except Exception:
            continue

    # Fallback: try to find ANY table with a "Player" column
    try:
        all_tables = pd.read_html(str(path))
        for df in all_tables:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[-1] for col in df.columns]
            if "Player" in df.columns and len(df) > 10:
                return _clean_df(df)
    except Exception as e:
        print(f"    ✗ Could not parse HTML {path.name}: {e}")
    return None


def read_table_from_csv(path: Path) -> pd.DataFrame | None:
    """Read an FBref 'Get table as CSV' export."""
    for skiprows in (1, 0):
        try:
            df = pd.read_csv(path, skiprows=skiprows, header=0,
                             encoding="utf-8-sig")
            if "Player" in df.columns:
                return _clean_df(df)
        except Exception:
            continue
    return None


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove repeated header rows and blank rows."""
    if "Player" in df.columns:
        df = df[df["Player"].astype(str) != "Player"]
        df = df[df["Player"].astype(str).str.strip() != ""]
        df = df.dropna(subset=["Player"])
    return df.reset_index(drop=True)


def read_file(path: Path, file_type: str) -> pd.DataFrame | None:
    table_ids = SHOOTING_TABLE_IDS if "shooting" in file_type else STANDARD_TABLE_IDS
    if path.suffix in (".html", ".htm"):
        return read_table_from_html(path, table_ids)
    else:
        return read_table_from_csv(path)


# ---------------------------------------------------------------------------
# Column extraction (handles FBref's many column name variations)
# ---------------------------------------------------------------------------

def col(df: pd.DataFrame, *aliases) -> str | None:
    for a in aliases:
        if a in df.columns:
            return a
    return None


def parse_standard_row(row, df: pd.DataFrame) -> dict | None:
    nineties = safe_float(row.get(col(df, "90s") or "", 0))
    minutes  = safe_float(row.get(col(df, "Min") or "", 0))
    mp       = safe_float(row.get(col(df, "MP", "Matches") or "", 0))
    starts   = safe_float(row.get(col(df, "Starts") or "", 0))
    goals    = safe_float(row.get(col(df, "Gls", "Goals") or "", 0))
    assists  = safe_float(row.get(col(df, "Ast", "Assists") or "", 0))
    xg       = safe_float(row.get(col(df, "xG") or "", 0))
    xag      = safe_float(row.get(col(df, "xAG", "xA") or "", 0))
    squad    = norm_club(str(row.get(col(df, "Squad") or "", "")).strip())

    if nineties <= 0 and minutes > 0:
        nineties = minutes / 90
    if nineties <= 0:
        return None

    return {
        "_squad":    squad,
        "_nineties": nineties,
        "mp":        int(mp),
        "starts":    int(starts),
        "minutes":   int(minutes) if minutes > 0 else int(nineties * 90),
        "goals90":   per90(goals, nineties),
        "xg90":      per90(xg, nineties),
        "xa90":      per90(xag, nineties),
        "starter_rate": round(starts / mp, 2) if mp > 0 else 0.0,
    }


def parse_shooting_row(row, df: pd.DataFrame) -> dict:
    # Prefer pre-computed /90 columns
    sot90 = safe_float(row.get(col(df, "SoT/90") or "", 0))
    sh90  = safe_float(row.get(col(df, "Sh/90") or "", 0))

    if sot90 == 0:
        nineties = safe_float(row.get(col(df, "90s") or "", 0))
        sot = safe_float(row.get(col(df, "SoT") or "", 0))
        sh  = safe_float(row.get(col(df, "Sh", "Shots") or "", 0))
        sot90 = per90(sot, nineties)
        sh90  = per90(sh, nineties)

    return {"sot90": sot90, "sh90": sh90}


def parse_df(df: pd.DataFrame, file_type: str) -> dict:
    """Returns {norm_player_name: stats_dict}."""
    result = {}
    pcol = col(df, "Player")
    if not pcol:
        return result

    for _, row in df.iterrows():
        pname = str(row.get(pcol, "")).strip()
        if not pname or pname in ("Player", "nan"):
            continue
        key = norm(pname)

        if "shooting" in file_type:
            result[key] = parse_shooting_row(row, df)
        else:
            parsed = parse_standard_row(row, df)
            if parsed:
                result[key] = parsed

    return result


# ---------------------------------------------------------------------------
# Build club stats
# ---------------------------------------------------------------------------

def build_club_stats(wc_players: dict) -> dict:
    standard_data: dict[str, dict] = {}
    shooting_data: dict[str, dict] = {}

    all_files = {**CLUB_FILES}

    for stem, (league, file_type) in all_files.items():
        path = find_file(stem)
        if not path:
            continue

        df = read_file(path, file_type)
        if df is None or df.empty:
            print(f"  {stem}: empty or unreadable")
            continue

        parsed = parse_df(df, file_type)
        print(f"  {path.name}: {len(parsed)} players ({league})")

        if "shooting" in file_type:
            shooting_data.update(parsed)
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

        out[norm_name] = {
            "name":         wcp["name"],
            "squad":        wcp["club"],
            "league":       std.get("_league", ""),
            "mp":           std["mp"],
            "starts":       std["starts"],
            "minutes":      std["minutes"],
            "xg90":         std["xg90"],
            "xa90":         std["xa90"],
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

        df = read_file(path, file_type)
        if df is None or df.empty:
            continue

        parsed = parse_df(df, "standard")
        shoot  = parse_df(df, "shooting") if "shooting" in (df.columns.tolist()) else {}
        print(f"  {path.name}: {len(parsed)} players ({comp})")

        for k, v in parsed.items():
            v["sot90"] = shoot.get(k, {}).get("sot90", 0.0)
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

    available = list(FBREF_DIR.glob("*"))
    data_files = [f for f in available if f.suffix in (".html", ".htm", ".csv")]

    if not data_files:
        print(f"No files found in {FBREF_DIR}")
        print("Save FBref pages as HTML (Ctrl+S / Cmd+S) into that folder.")
        print("See FBREF_DOWNLOAD_GUIDE.md for filenames and URLs.")
        return

    print(f"Found {len(data_files)} files in {FBREF_DIR}\n")

    wc_players = load_squads()
    print(f"Loaded {len(wc_players)} WC players\n")

    print("=== Club stats ===")
    club_stats = build_club_stats(wc_players)

    print("\n=== NT stats ===")
    nt_stats = build_nt_stats(wc_players)

    if args.dry_run:
        print("\n[dry-run] First 3 club entries:")
        for k, v in list(club_stats.items())[:3]:
            print(f"  {k}: xg90={v['xg90']} xa90={v['xa90']} sot90={v['sot90']}")
        print("\n[dry-run] First 3 NT entries:")
        for k, v in list(nt_stats.items())[:3]:
            print(f"  {k}: nation={v['nation']} xg90={v['xg90']} goals90={v['goals90']}")
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
