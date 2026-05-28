#!/usr/bin/env python3
"""
Scrape FBref season stats for WC 2026 qualifying leagues.
Run LOCALLY before deploying: python fetch_fbref.py

Output: data/fbref_stats.json  (list of player stat dicts)
Cache:  data/fbref_cache.json  (per-league raw records, skipped on re-run)

Usage:
    python fetch_fbref.py           # use cache if available
    python fetch_fbref.py --refresh # ignore cache, re-fetch all
"""
import io
import json
import os
import sys
import time
import unicodedata

import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://fbref.com/",
}

DELAY       = 3.5   # seconds between requests (FBref rate-limit guard)
CACHE_FILE  = "data/fbref_cache.json"
OUTPUT_FILE = "data/fbref_stats.json"

# league label -> (comp_id, URL slug)
LEAGUES: dict[str, tuple[int, str]] = {
    "PL":           (9,  "Premier-League"),
    "LaLiga":       (12, "La-Liga"),
    "SerieA":       (11, "Serie-A"),
    "Bundesliga":   (20, "Bundesliga"),
    "Ligue1":       (13, "Ligue-1"),
    "LigaMX":       (31, "Liga-MX"),
    "MLS":          (22, "Major-League-Soccer"),
    "Saudi":        (70, "Saudi-Pro-League"),
    "Eredivisie":   (23, "Eredivisie"),
    "PrimeiraLiga": (32, "Primeira-Liga"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_name(name: str) -> str:
    name = name.lower().replace("ı", "i")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(val) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _load_cache() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> str:
    """GET with rate-limit delay and retries. Returns HTML string or empty."""
    time.sleep(DELAY)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"    Rate-limited. Waiting {wait}s ...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.text
        except requests.exceptions.HTTPError as e:
            print(f"    [HTTP {r.status_code}] {url}: {e}")
            return ""
        except Exception as e:
            print(f"    [ERROR] {url}: {e}")
            return ""
    return ""


# ── Table parsing ─────────────────────────────────────────────────────────────

def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten FBref multi-level headers. Duplicate bottom-level names get _1, _2 suffixes."""
    if not isinstance(df.columns, pd.MultiIndex):
        return df
    seen: dict[str, int] = {}
    new_cols: list[str] = []
    for levels in df.columns:
        col = str(levels[-1])  # last level is always the stat name
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols
    return df


def _read_table(html: str, *table_ids: str) -> pd.DataFrame | None:
    """Try each table_id in order; return first matching DataFrame or None."""
    for tid in table_ids:
        try:
            tables = pd.read_html(io.StringIO(html), attrs={"id": tid})
            if tables:
                return _flatten_cols(tables[0])
        except ValueError:
            continue
        except Exception as e:
            print(f"    [parse] {tid}: {e}")
    return None


def _parse_standard(html: str, league: str) -> list[dict]:
    """Extract per-player stats from stats_standard table."""
    df = _read_table(html, "stats_standard")
    if df is None:
        return []

    # Drop repeated header rows that FBref embeds mid-table
    if "Player" in df.columns:
        df = df[df["Player"].astype(str).str.strip() != "Player"]
        df = df.dropna(subset=["Player"])

    players: list[dict] = []
    for _, row in df.iterrows():
        name = str(row.get("Player", "")).strip()
        if not name or name in ("Player", "nan"):
            continue

        squad  = str(row.get("Squad", "")).strip()
        pos    = str(row.get("Pos",   "")).strip()[:2].upper()
        mp     = _safe_int(row.get("MP",    0))
        starts = _safe_int(row.get("Starts", 0))
        min_   = _safe_int(row.get("Min",   0))
        s90    = _safe_float(row.get("90s",  0))
        gls    = _safe_float(row.get("Gls",  0))
        ast    = _safe_float(row.get("Ast",  0))
        xg     = _safe_float(row.get("xG",   0))
        xag    = _safe_float(row.get("xAG",  0))

        if s90 <= 0 or mp == 0:
            continue

        players.append({
            "name":         name,
            "norm_name":    _norm_name(name),
            "squad":        squad,
            "pos":          pos,
            "league":       league,
            "mp":           mp,
            "starts":       starts,
            "min":          min_,
            "90s":          s90,
            "goals":        gls,
            "assists":      ast,
            "xg":           xg,
            "xag":          xag,
            "xg90":         round(xg  / s90, 4) if s90 > 0 else 0.0,
            "xa90":         round(xag / s90, 4) if s90 > 0 else 0.0,
            "goals90":      round(gls / s90, 4) if s90 > 0 else 0.0,
            "sot90":        0.0,   # filled in from shooting page
            "starter_rate": round(starts / mp, 3) if mp > 0 else 1.0,
        })
    return players


def _parse_shooting_sot(html: str) -> dict[str, float]:
    """Return {norm_name -> sot/90} from stats_shooting table."""
    df = _read_table(html, "stats_shooting", "stats_shooting_sq", "stats_shooting_sq_gk")
    if df is None:
        return {}

    if "Player" in df.columns:
        df = df[df["Player"].astype(str).str.strip() != "Player"]
        df = df.dropna(subset=["Player"])

    sot_map: dict[str, float] = {}
    for _, row in df.iterrows():
        name = str(row.get("Player", "")).strip()
        if not name or name == "nan":
            continue
        s90 = _safe_float(row.get("90s", 0))
        sot = _safe_float(row.get("SoT", 0))
        if s90 > 0:
            sot_map[_norm_name(name)] = round(sot / s90, 4)
    return sot_map


# ── Main ──────────────────────────────────────────────────────────────────────

def main(force_refresh: bool = False) -> None:
    cache = {} if force_refresh else _load_cache()
    all_players: list[dict] = []
    requests_made = 0

    for league, (comp_id, slug) in LEAGUES.items():
        std_url = f"https://fbref.com/en/comps/{comp_id}/stats/{slug}-Stats"
        sht_url = f"https://fbref.com/en/comps/{comp_id}/shooting/{slug}-Stats"
        cache_key_std = f"{league}_standard"
        cache_key_sht = f"{league}_shooting"

        print(f"\n{league} ({comp_id})...")

        # ── Standard stats ──
        if cache_key_std in cache and not force_refresh:
            players = cache[cache_key_std]
            print(f"  standard: {len(players)} players (cached)")
        else:
            print(f"  fetching standard: {std_url}")
            html = _fetch_html(std_url)
            requests_made += 1
            if not html:
                print("  [SKIP] No HTML received")
                continue
            players = _parse_standard(html, league)
            if not players:
                print("  [WARN] No players parsed from standard table")
                continue
            cache[cache_key_std] = players
            _save_cache(cache)
            print(f"  standard: {len(players)} players")

        # ── Shooting stats ──
        if cache_key_sht in cache and not force_refresh:
            sot_map = cache[cache_key_sht]
            print(f"  shooting: {len(sot_map)} entries (cached)")
        else:
            print(f"  fetching shooting: {sht_url}")
            html = _fetch_html(sht_url)
            requests_made += 1
            if not html:
                sot_map = {}
                print("  [WARN] No HTML for shooting — sot90 will be 0")
            else:
                sot_map = _parse_shooting_sot(html)
                cache[cache_key_sht] = sot_map
                _save_cache(cache)
                print(f"  shooting: {len(sot_map)} entries")

        # Merge sot90 into player records
        for p in players:
            p["sot90"] = sot_map.get(p["norm_name"], 0.0)

        all_players.extend(players)

    # Deduplicate: if a player appears in multiple leagues, keep the one
    # with the most 90s played (they may have transferred mid-season).
    deduped: dict[str, dict] = {}
    for p in all_players:
        key = p["norm_name"]
        if key not in deduped or p["90s"] > deduped[key]["90s"]:
            deduped[key] = p

    result = list(deduped.values())
    result.sort(key=lambda x: (-x["xg90"], x["name"]))

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*55}")
    print(f"Saved  → {OUTPUT_FILE}")
    print(f"Players: {len(result)} unique (from {len(all_players)} total)")
    print(f"Requests: {requests_made} made this run")
    print(f"\nNext: python name_match.py")


if __name__ == "__main__":
    force = "--refresh" in sys.argv
    main(force_refresh=force)
