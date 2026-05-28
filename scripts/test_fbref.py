"""
Quick test: can we reach FBref and parse a stats table?

Run this locally (NOT in the cloud sandbox) before building the full pipeline:
    pip install requests pandas lxml beautifulsoup4
    python scripts/test_fbref.py

If it prints player rows, FBref works and we can build the full pipeline.
"""

import time
import requests
import pandas as pd

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
}

# FBref comp IDs for 2025-26
LEAGUES = {
    "Premier League":  ("9",  "2025-2026-Premier-League-Stats"),
    "La Liga":         ("12", "2025-2026-La-Liga-Stats"),
    "Bundesliga":      ("20", "2025-2026-Bundesliga-Stats"),
    "Serie A":         ("11", "2025-2026-Serie-A-Stats"),
    "Ligue 1":         ("13", "2025-2026-Ligue-1-Stats"),
}


def fetch_league(name: str, comp_id: str, slug: str) -> pd.DataFrame | None:
    url = f"https://fbref.com/en/comps/{comp_id}/stats/players/{slug}"
    print(f"\n→ {name}: {url}")
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.get(url, timeout=20)
        print(f"  HTTP {resp.status_code}")
        if resp.status_code != 200:
            return None
        tables = pd.read_html(resp.text, attrs={"id": "stats_standard"})
        if not tables:
            print("  ⚠ No table found")
            return None
        df = tables[0]
        # flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join(c).strip() for c in df.columns]
        print(f"  ✓ {len(df)} rows, columns: {list(df.columns[:8])}")
        return df
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


if __name__ == "__main__":
    print("Testing FBref access...\n")
    for name, (comp_id, slug) in LEAGUES.items():
        df = fetch_league(name, comp_id, slug)
        if df is not None:
            sample = df[df.get("Player", df.columns[0]).astype(str) != "Player"].head(3)
            print(f"  Sample rows:\n{sample.iloc[:, :6].to_string()}\n")
        time.sleep(4)  # be polite, avoid rate-limit
    print("\nDone. If you saw player data above, FBref works — run the full pipeline.")
