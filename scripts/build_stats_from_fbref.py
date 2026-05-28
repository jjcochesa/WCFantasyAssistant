"""
build_stats_from_fbref.py

Reads FBref CSV exports from data/fbref/ and writes:
  data/manual_stats.json      (2025/26 club stats)
  data/manual_nt_stats.json   (WC 2026 qualifying NT stats)

See FBREF_DOWNLOAD_GUIDE.md for exactly which pages to download.

Usage:
    python scripts/build_stats_from_fbref.py [--dry-run]

Requirements: pip install pandas lxml (requests not needed — CSVs are local)
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
# FBref CSV file names → league metadata
# Place downloaded CSVs in data/fbref/ with these exact file names
# ---------------------------------------------------------------------------

CLUB_CSVS = {
    # file_name: (league_display_name, competition)
    "club_PL_standard.csv":      ("Premier League", "eng ENG"),
    "club_PL_shooting.csv":      ("Premier League", "eng ENG"),
    "club_LaLiga_standard.csv":  ("La Liga", "es ESP"),
    "club_LaLiga_shooting.csv":  ("La Liga", "es ESP"),
    "club_Bundesliga_standard.csv": ("Bundesliga", "de GER"),
    "club_Bundesliga_shooting.csv": ("Bundesliga", "de GER"),
    "club_SerieA_standard.csv":  ("Serie A", "it ITA"),
    "club_SerieA_shooting.csv":  ("Serie A", "it ITA"),
    "club_Ligue1_standard.csv":  ("Ligue 1", "fr FRA"),
    "club_Ligue1_shooting.csv":  ("Ligue 1", "fr FRA"),
    "club_Saudi_standard.csv":   ("Saudi Pro League", "sa KSA"),
    "club_Saudi_shooting.csv":   ("Saudi Pro League", "sa KSA"),
    "club_Eredivisie_standard.csv": ("Eredivisie", "nl NED"),
    "club_Eredivisie_shooting.csv": ("Eredivisie", "nl NED"),
    "club_PrimeiraLiga_standard.csv": ("Primeira Liga", "pt POR"),
    "club_PrimeiraLiga_shooting.csv": ("Primeira Liga", "pt POR"),
    "club_SuperLig_standard.csv":("Süper Lig", "tr TUR"),
    "club_SuperLig_shooting.csv":("Süper Lig", "tr TUR"),
    "club_Scottish_standard.csv":("Scottish Prem", "sco SCO"),
    "club_Scottish_shooting.csv":("Scottish Prem", "sco SCO"),
    "club_Belgian_standard.csv": ("Belgian Pro League", "be BEL"),
    "club_Belgian_shooting.csv": ("Belgian Pro League", "be BEL"),
    "club_MLS_standard.csv":     ("MLS", "us USA"),
    "club_MLS_shooting.csv":     ("MLS", "us USA"),
    "club_LigaMX_standard.csv":  ("Liga MX", "mx MEX"),
    "club_LigaMX_shooting.csv":  ("Liga MX", "mx MEX"),
    "club_BrazilA_standard.csv": ("Série A (Brazil)", "br BRA"),
    "club_BrazilA_shooting.csv": ("Série A (Brazil)", "br BRA"),
    "club_Argentina_standard.csv": ("Primera Div (ARG)", "ar ARG"),
    "club_Argentina_shooting.csv": ("Primera Div (ARG)", "ar ARG"),
}

NT_CSVS = {
    # file_name: confederation
    "nt_UEFA_WC.csv":     "UEFA",
    "nt_CONMEBOL_WC.csv": "CONMEBOL",
    "nt_CAF_WC.csv":      "CAF",
    "nt_CONCACAF_WC.csv": "CONCACAF",
    "nt_AFC_WC.csv":      "AFC",
    "nt_AFCON2025.csv":   "CAF",   # supplement for African players
    "nt_CopaAmerica2024.csv": "CONMEBOL",
    "nt_UEFANationsLeague.csv": "UEFA",
}

# ---------------------------------------------------------------------------
# Club name → FBref squad name mapping (FBref uses different spellings)
# ---------------------------------------------------------------------------

CLUB_ALIASES = {
    "man utd": "manchester utd",
    "man city": "manchester city",
    "nottm forest": "nott'ham forest",
    "ac milan": "milan",
    "borussia dortmund": "dortmund",
    "borussia m'gladbach": "m'gladbach",
    "atletico madrid": "atlético madrid",
    "athletic bilbao": "athletic club",
    "al-hilal": "al-hilal",
    "al-nassr": "al-nassr",
    "al-ahli": "al-ahli",
    "al-qadsiah": "al-qadsiah",
    "psg": "paris s-g",
    "inter milan": "inter",
    "rb leipzig": "rb leipzig",
    "leipzig": "rb leipzig",
    "bayer leverkusen": "leverkusen",
    "sporting cp": "sporting cp",
    "la galaxy": "la galaxy",
    "lafc": "los angeles fc",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def norm(name: str) -> str:
    """Strip accents and lowercase."""
    s = unicodedata.normalize("NFKD", str(name))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def norm_club(name: str) -> str:
    n = norm(name)
    return CLUB_ALIASES.get(n, n)


def load_squads() -> dict:
    """Returns {norm_name: {name, nation, club, position}} for all WC players."""
    sq = json.load(open(SQUADS_FILE))
    players = {}
    for nation_code, team_data in sq["teams"].items():
        for p in team_data["players"]:
            key = norm(p["name"])
            players[key] = {
                "name": p["name"],
                "nation": nation_code,
                "club": p.get("club", ""),
                "position": p.get("position", "MID"),
            }
    return players


def read_fbref_csv(path: Path) -> pd.DataFrame | None:
    """
    Read an FBref 'Get table as CSV' export.
    FBref CSVs have a two-row header. We skip the first row (category row)
    and use the second row as column names. Repeated header rows are dropped.
    """
    try:
        df = pd.read_csv(path, skiprows=1, header=0, encoding="utf-8-sig")
    except Exception:
        try:
            df = pd.read_csv(path, skiprows=0, header=0, encoding="utf-8-sig")
        except Exception as e:
            print(f"  ✗ Could not read {path.name}: {e}")
            return None

    # Drop repeated header rows (FBref inserts column names every 25 rows)
    if "Player" in df.columns:
        df = df[df["Player"] != "Player"].copy()
    elif "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"].copy()

    # Drop totals / squad rows
    df = df.dropna(subset=["Player"] if "Player" in df.columns else df.columns[:2])
    df = df[df.get("Player", df.iloc[:, 1]).astype(str).str.strip() != ""].copy()

    return df.reset_index(drop=True)


def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return f if pd.notna(f) else default
    except (ValueError, TypeError):
        return default


def per90(total: float, nineties: float) -> float:
    if nineties <= 0:
        return 0.0
    return round(total / nineties, 3)


# ---------------------------------------------------------------------------
# Standard stats processing
# ---------------------------------------------------------------------------

STANDARD_COLS = {
    "Player": ["Player"],
    "Squad":  ["Squad"],
    "90s":    ["90s"],
    "MP":     ["MP", "Matches"],
    "Starts": ["Starts"],
    "Min":    ["Min"],
    "Gls":    ["Gls", "Goals"],
    "Ast":    ["Ast", "Assists"],
    "xG":     ["xG"],
    "xAG":    ["xAG", "xA"],
    "npxG":   ["npxG"],
}

SHOOTING_COLS = {
    "Player": ["Player"],
    "Squad":  ["Squad"],
    "SoT":    ["SoT", "Sh on Target"],
    "Sh":     ["Sh", "Shots"],
    "90s":    ["90s"],
    "SoT_90": ["SoT/90"],
    "Sh_90":  ["Sh/90"],
}


def find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    for a in aliases:
        if a in df.columns:
            return a
    return None


def parse_standard(df: pd.DataFrame) -> dict:
    """Returns {norm_player: stats_dict} from a standard stats CSV."""
    result = {}
    pcol = find_col(df, STANDARD_COLS["Player"])
    scol = find_col(df, STANDARD_COLS["Squad"])
    if not pcol:
        return result

    for _, row in df.iterrows():
        pname = str(row.get(pcol, "")).strip()
        if not pname or pname == "Player":
            continue
        key = norm(pname)

        nineties = safe_float(row.get(find_col(df, STANDARD_COLS["90s"]) or "", 0))
        mp       = safe_float(row.get(find_col(df, STANDARD_COLS["MP"]) or "", 0))
        starts   = safe_float(row.get(find_col(df, STANDARD_COLS["Starts"]) or "", 0))
        minutes  = safe_float(row.get(find_col(df, STANDARD_COLS["Min"]) or "", 0))
        goals    = safe_float(row.get(find_col(df, STANDARD_COLS["Gls"]) or "", 0))
        assists  = safe_float(row.get(find_col(df, STANDARD_COLS["Ast"]) or "", 0))
        xg       = safe_float(row.get(find_col(df, STANDARD_COLS["xG"]) or "", 0))
        xag      = safe_float(row.get(find_col(df, STANDARD_COLS["xAG"]) or "", 0))

        squad = norm_club(str(row.get(scol, "")).strip()) if scol else ""

        if nineties <= 0 and minutes > 0:
            nineties = minutes / 90

        result[key] = {
            "_squad": squad,
            "_nineties": nineties,
            "mp": int(mp),
            "starts": int(starts),
            "minutes": int(minutes),
            "goals90": per90(goals, nineties),
            "xg90": per90(xg, nineties),
            "xa90": per90(xag, nineties),
            "starter_rate": round(starts / mp, 2) if mp > 0 else 0.0,
        }
    return result


def parse_shooting(df: pd.DataFrame) -> dict:
    """Returns {norm_player: {sot90, sh90}} from a shooting CSV."""
    result = {}
    pcol = find_col(df, SHOOTING_COLS["Player"])
    if not pcol:
        return result

    for _, row in df.iterrows():
        pname = str(row.get(pcol, "")).strip()
        if not pname or pname == "Player":
            continue
        key = norm(pname)

        # Prefer pre-computed /90 columns; fall back to computing from totals
        sot90_col = find_col(df, SHOOTING_COLS["SoT_90"])
        sh90_col  = find_col(df, SHOOTING_COLS["Sh_90"])

        if sot90_col and sh90_col:
            sot90 = safe_float(row.get(sot90_col, 0))
            sh90  = safe_float(row.get(sh90_col, 0))
        else:
            nineties = safe_float(row.get(find_col(df, SHOOTING_COLS["90s"]) or "", 0))
            sot = safe_float(row.get(find_col(df, SHOOTING_COLS["SoT"]) or "", 0))
            sh  = safe_float(row.get(find_col(df, SHOOTING_COLS["Sh"]) or "", 0))
            sot90 = per90(sot, nineties)
            sh90  = per90(sh, nineties)

        result[key] = {"sot90": sot90, "sh90": sh90}
    return result


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------

def build_club_stats(wc_players: dict) -> dict:
    """
    Merge all available standard + shooting CSVs into per-player club stats.
    For players who appear in multiple league files (transfers), prefer
    the file with more minutes.
    """
    standard_data: dict[str, dict] = {}  # norm_name → stats
    shooting_data: dict[str, dict] = {}  # norm_name → {sot90, sh90}

    for fname, (league, _) in CLUB_CSVS.items():
        fpath = FBREF_DIR / fname
        if not fpath.exists():
            continue

        df = read_fbref_csv(fpath)
        if df is None or df.empty:
            continue

        if "shooting" in fname:
            parsed = parse_shooting(df)
            print(f"  {fname}: {len(parsed)} shooting rows")
            for k, v in parsed.items():
                shooting_data[k] = v
        else:
            parsed = parse_standard(df)
            print(f"  {fname}: {len(parsed)} standard rows")
            for k, v in parsed.items():
                # keep entry with most minutes if player appears in multiple leagues
                existing = standard_data.get(k)
                if existing is None or v["minutes"] > existing["minutes"]:
                    v["_league"] = league
                    standard_data[k] = v

    print(f"\nStandard data loaded: {len(standard_data)} players")
    print(f"Shooting data loaded:  {len(shooting_data)} players")

    # --- merge into output dict ---
    out = {}
    matched = 0

    for norm_name, wcp in wc_players.items():
        std = standard_data.get(norm_name)
        if std is None:
            continue  # no FBref club match

        sht = shooting_data.get(norm_name, {})
        matched += 1

        entry = {
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
        out[norm_name] = entry

    print(f"WC players matched to club stats: {matched}/{len(wc_players)}")
    unmatched = [wcp["name"] for nn, wcp in wc_players.items() if nn not in out]
    if unmatched:
        print(f"Unmatched ({len(unmatched)}): {unmatched[:10]}{'...' if len(unmatched) > 10 else ''}")
    return out


def build_nt_stats(wc_players: dict) -> dict:
    """
    Merge all NT qualification CSVs. For players with multiple entries
    (different competitions), average weighted by 90s played.
    """
    nt_raw: dict[str, list] = defaultdict(list)  # norm_name → list of stat dicts

    for fname, conf in NT_CSVS.items():
        fpath = FBREF_DIR / fname
        if not fpath.exists():
            continue

        df = read_fbref_csv(fpath)
        if df is None or df.empty:
            continue

        parsed = parse_standard(df)
        shoot  = parse_shooting(df)
        print(f"  {fname}: {len(parsed)} NT rows ({conf})")

        for norm_name, stats in parsed.items():
            entry = {**stats, "_conf": conf}
            entry["sot90"] = shoot.get(norm_name, {}).get("sot90", 0.0)
            nt_raw[norm_name].append(entry)

    out = {}
    matched = 0

    for norm_name, wcp in wc_players.items():
        rows = nt_raw.get(norm_name)
        if not rows:
            continue

        matched += 1
        # weighted average of per-90 rates by minutes played
        total_min = sum(r["minutes"] for r in rows) or 1
        def wavg(field):
            return round(sum(r.get(field, 0) * r["minutes"] for r in rows) / total_min, 3)

        total_mp  = sum(r["mp"] for r in rows)
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
            "tackles90":    wavg("tackles90") if any("tackles90" in r for r in rows) else 0.0,
        }

    print(f"WC players matched to NT stats: {matched}/{len(wc_players)}")
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing files")
    args = parser.parse_args()

    if not FBREF_DIR.exists():
        print(f"Creating {FBREF_DIR}")
        FBREF_DIR.mkdir(parents=True)

    available = list(FBREF_DIR.glob("*.csv"))
    if not available:
        print(f"No CSVs found in {FBREF_DIR}")
        print("Download FBref CSVs as described in FBREF_DOWNLOAD_GUIDE.md")
        return

    print(f"Found {len(available)} CSV files in {FBREF_DIR}\n")
    wc_players = load_squads()
    print(f"Loaded {len(wc_players)} WC players from wc_squads.json\n")

    print("--- Club stats ---")
    club_stats = build_club_stats(wc_players)

    print("\n--- NT stats ---")
    nt_stats = build_nt_stats(wc_players)

    if args.dry_run:
        print("\n[dry-run] Sample club stats (first 3):")
        for k, v in list(club_stats.items())[:3]:
            print(f"  {k}: {v}")
        print("\n[dry-run] Sample NT stats (first 3):")
        for k, v in list(nt_stats.items())[:3]:
            print(f"  {k}: {v}")
        return

    # Merge with existing files (preserve entries not found in FBref)
    existing_club = json.loads(OUT_CLUB.read_text()) if OUT_CLUB.exists() else {}
    existing_nt   = json.loads(OUT_NT.read_text()) if OUT_NT.exists() else {}

    existing_club.update(club_stats)
    existing_nt.update(nt_stats)

    OUT_CLUB.write_text(json.dumps(existing_club, indent=2, ensure_ascii=False))
    OUT_NT.write_text(json.dumps(existing_nt, indent=2, ensure_ascii=False))

    print(f"\n✓ Wrote {len(existing_club)} entries → {OUT_CLUB}")
    print(f"✓ Wrote {len(existing_nt)} entries → {OUT_NT}")
    print("\nPlayers NOT found in FBref keep their existing manual stats.")


if __name__ == "__main__":
    main()
