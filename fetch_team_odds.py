"""
Scrape FPLJoe.com WC odds → refresh data/team_stats.py PROJ_GOALS and CS_PCT.

Run from your Mac:
    python fetch_team_odds.py            # scrape & update
    python fetch_team_odds.py --dry-run  # print what would change, no write

Data source: https://www.fpljoe.com/?mode=world-cup (SBOBET / Betfair markets)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Mapping: FPLJoe display name → our 3-letter code
# ---------------------------------------------------------------------------
FPLJOE_NAME_TO_CODE: dict[str, str] = {
    "Argentina": "ARG", "Australia": "AUS", "Austria": "AUT",
    "Belgium": "BEL", "Bosnia-Herzegovina": "BIH", "Bosnia": "BIH",
    "Brazil": "BRA", "Canada": "CAN", "Cape Verde": "CPV",
    "Colombia": "COL", "Croatia": "CRO", "Czech Republic": "CZE",
    "DR Congo": "COD", "Ecuador": "ECU", "Egypt": "EGY",
    "England": "ENG", "France": "FRA", "Germany": "GER",
    "Ghana": "GHA", "Haiti": "HAI", "Iran": "IRN",
    "Iraq": "IRQ", "Ivory Coast": "CIV", "Cote d'Ivoire": "CIV",
    "Japan": "JPN", "Jordan": "JOR", "Morocco": "MAR",
    "Mexico": "MEX", "Netherlands": "NED", "New Zealand": "NZL",
    "Norway": "NOR", "Panama": "PAN", "Paraguay": "PAR",
    "Portugal": "POR", "Qatar": "QAT", "Saudi Arabia": "KSA",
    "Scotland": "SCO", "Senegal": "SEN", "South Africa": "RSA",
    "South Korea": "KOR", "Spain": "ESP", "Sweden": "SWE",
    "Switzerland": "SUI", "Tunisia": "TUN", "Turkey": "TUR",
    "Uruguay": "URU", "USA": "USA", "United States": "USA",
    "Uzbekistan": "UZB", "Curacao": "CUW", "Algeria": "ALG",
}

URL = "https://www.fpljoe.com/?mode=world-cup"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fpljoe.com/",
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_html() -> str:
    print(f"Fetching {URL} …")
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    print(f"  HTTP {r.status_code}, {len(r.text):,} chars")
    return r.text


# ---------------------------------------------------------------------------
# Parse strategies
# ---------------------------------------------------------------------------

def _extract_next_data(html: str) -> dict | None:
    """Try Next.js __NEXT_DATA__ embedded JSON — often contains the full dataset."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_next_data(data: dict) -> tuple[dict, dict] | None:
    """
    Walk the Next.js props tree looking for team odds arrays.
    Returns (proj_goals, cs_pct) dicts keyed by 3-letter code, or None.
    """
    raw = json.dumps(data)

    # Heuristic: look for arrays of dicts that have team + cs / goals keys
    # Try to find the pageProps section
    try:
        page_props = data["props"]["pageProps"]
    except (KeyError, TypeError):
        page_props = {}

    # Dump and look for known field patterns
    candidates = re.findall(
        r'\{[^{}]*"team"\s*:\s*"([^"]+)"[^{}]*"cs"\s*:\s*(\[[\d.,\s]+\])[^{}]*"goals"\s*:\s*(\[[\d.,\s]+\])[^{}]*\}',
        raw,
    )
    if candidates:
        proj_goals, cs_pct = {}, {}
        for name, cs_raw, g_raw in candidates:
            code = FPLJOE_NAME_TO_CODE.get(name)
            if code:
                cs_pct[code]    = json.loads(cs_raw)
                proj_goals[code] = json.loads(g_raw)
        if proj_goals:
            return proj_goals, cs_pct

    # Alternative key names
    candidates2 = re.findall(
        r'\{[^{}]*"name"\s*:\s*"([^"]+)"[^{}]*"cleanSheet"\s*:\s*(\[[\d.,\s]+\])[^{}]*"xg"\s*:\s*(\[[\d.,\s]+\])[^{}]*\}',
        raw,
    )
    if candidates2:
        proj_goals, cs_pct = {}, {}
        for name, cs_raw, g_raw in candidates2:
            code = FPLJOE_NAME_TO_CODE.get(name)
            if code:
                cs_pct[code]    = json.loads(cs_raw)
                proj_goals[code] = json.loads(g_raw)
        if proj_goals:
            return proj_goals, cs_pct

    return None


def _parse_html_tables(html: str) -> tuple[dict, dict] | None:
    """
    Fall back: parse the visible HTML tables with lxml.
    FPLJoe typically renders a table per group or a single large table.
    """
    try:
        from lxml import etree
        from io import StringIO
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(html), parser)
    except Exception as e:
        print(f"  [warn] lxml parse failed: {e}")
        return None

    rows = tree.xpath("//table//tr")
    if not rows:
        # Try divs that look like rows
        print("  [warn] No <table> rows found in HTML")
        return None

    proj_goals: dict[str, list[float]] = {}
    cs_pct:     dict[str, list[float]] = {}

    for row in rows:
        cells = [c.text_content().strip() for c in row.xpath(".//td|.//th")]
        if not cells:
            continue
        # First cell is likely the team name
        team_name = cells[0]
        code = FPLJOE_NAME_TO_CODE.get(team_name)
        if not code or len(cells) < 7:
            continue
        # Expected column order (example): Team | MD1 xG | MD2 xG | MD3 xG | MD1 CS | MD2 CS | MD3 CS
        # Exact order depends on FPLJoe layout — adjust indices if needed
        try:
            g_vals = [float(cells[1]), float(cells[2]), float(cells[3])]
            cs_vals = [float(cells[4].strip("%")) / 100,
                       float(cells[5].strip("%")) / 100,
                       float(cells[6].strip("%")) / 100]
            proj_goals[code] = g_vals
            cs_pct[code]     = cs_vals
        except (ValueError, IndexError):
            continue

    if not proj_goals:
        # Try transposed layout: rows are stats, columns are teams
        return _parse_transposed_table(tree)

    return proj_goals, cs_pct


def _parse_transposed_table(tree) -> tuple[dict, dict] | None:
    """Some FPLJoe layouts have teams as columns."""
    headers = tree.xpath("//table//tr[1]/th|//table//tr[1]/td")
    team_names = [h.text_content().strip() for h in headers]
    codes = [FPLJOE_NAME_TO_CODE.get(n) for n in team_names]

    rows = tree.xpath("//table//tr")
    goals_rows = []
    cs_rows    = []

    for row in rows:
        cells = [c.text_content().strip() for c in row.xpath(".//td|.//th")]
        label = cells[0].lower() if cells else ""
        if "goal" in label or "xg" in label:
            goals_rows.append(cells[1:])
        elif "cs" in label or "clean" in label:
            cs_rows.append(cells[1:])

    if not goals_rows or not cs_rows:
        return None

    proj_goals, cs_pct = {}, {}
    for i, code in enumerate(codes):
        if not code:
            continue
        try:
            proj_goals[code] = [float(goals_rows[md][i]) for md in range(min(3, len(goals_rows)))]
            cs_pct[code]     = [float(cs_rows[md][i].strip("%")) / 100 for md in range(min(3, len(cs_rows)))]
        except (ValueError, IndexError):
            continue

    return (proj_goals, cs_pct) if proj_goals else None


def _parse_inline_json(html: str) -> tuple[dict, dict] | None:
    """Look for any inline JSON blob that has enough team entries."""
    # Find JSON objects/arrays in <script> tags
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
    for script in scripts:
        # Look for assignments like `var data = [...]` or `window.__DATA__ = {...}`
        blobs = re.findall(r'(?:=\s*|:\s*)(\[{.*?}\]|\{{.*?\}})', script, re.S)
        for blob in blobs:
            try:
                obj = json.loads(blob)
            except json.JSONDecodeError:
                continue
            # Check if it looks like team odds data
            if isinstance(obj, list) and len(obj) > 20:
                proj_goals, cs_pct = {}, {}
                for item in obj:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("team") or item.get("name") or item.get("country") or ""
                    code = FPLJOE_NAME_TO_CODE.get(name)
                    if not code:
                        continue
                    g = item.get("goals") or item.get("xg") or item.get("scored") or []
                    c = item.get("cs") or item.get("cleanSheet") or item.get("clean_sheet") or []
                    if isinstance(g, list) and len(g) >= 3:
                        proj_goals[code] = [float(x) for x in g[:3]]
                    if isinstance(c, list) and len(c) >= 3:
                        cs_pct[code] = [float(x) for x in c[:3]]
                if len(proj_goals) > 20:
                    return proj_goals, cs_pct
    return None


# ---------------------------------------------------------------------------
# Update team_stats.py
# ---------------------------------------------------------------------------

STATS_PATH = Path(__file__).parent / "data" / "team_stats.py"


def _format_dict(name: str, data: dict[str, list], timestamp: str = "") -> str:
    comment = f"  # Updated: {timestamp}" if timestamp else ""
    lines = [f"{name} = {{{comment}"]
    items = list(data.items())
    for i in range(0, len(items), 4):
        chunk = items[i:i+4]
        lines.append("    " + ", ".join(f'"{k}": {v}' for k, v in chunk) + ",")
    lines.append("}")
    return "\n".join(lines)


def _update_team_stats(proj_goals: dict, cs_pct: dict, dry_run: bool) -> None:
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    src = STATS_PATH.read_text()

    new_goals = _format_dict("PROJ_GOALS", {k: [round(v, 2) for v in vals] for k, vals in proj_goals.items()}, ts)
    new_cs    = _format_dict("CS_PCT",     {k: [round(v, 3) for v in vals] for k, vals in cs_pct.items()}, ts)

    # Values in PROJ_GOALS and CS_PCT are lists (no nested {}), so [^}]* suffices.
    src_new = re.sub(r'PROJ_GOALS\s*=\s*\{[^}]*\}', new_goals, src, flags=re.S)
    src_new = re.sub(r'CS_PCT\s*=\s*\{[^}]*\}',     new_cs,    src_new, flags=re.S)

    if src_new == src:
        print("[warn] Regex replacement made no changes — check block format in team_stats.py")

    if dry_run:
        print("\n--- DRY RUN: would write to data/team_stats.py ---")
        # Show diff summary
        old_goals_m = re.search(r'PROJ_GOALS\s*=\s*\{.*?\}', src, re.S)
        if old_goals_m:
            old_vals = re.findall(r'"([A-Z]{3})":\s*\[([\d.,\s]+)\]', old_goals_m.group())
            old_dict = {k: [float(x) for x in v.split(",")] for k, v in old_vals}
            changed = [(k, old_dict.get(k), proj_goals[k]) for k in proj_goals
                       if old_dict.get(k) != proj_goals[k]]
            if changed:
                print(f"  PROJ_GOALS changes ({len(changed)} teams):")
                for k, old, new in changed[:10]:
                    print(f"    {k}: {old} → {new}")
                if len(changed) > 10:
                    print(f"    … and {len(changed)-10} more")
            else:
                print("  PROJ_GOALS: no changes")
    else:
        STATS_PATH.write_text(src_new)
        print(f"Wrote updated PROJ_GOALS + CS_PCT to {STATS_PATH}")
        print("  Remember to git add data/team_stats.py && git commit && git push")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh FPLJoe.com WC odds in data/team_stats.py")
    ap.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    ap.add_argument("--html-file", help="Parse a local HTML file instead of fetching (for debugging)")
    args = ap.parse_args()

    if args.html_file:
        html = Path(args.html_file).read_text()
        print(f"Using local file: {args.html_file}")
    else:
        try:
            html = _fetch_html()
        except requests.HTTPError as e:
            print(f"\nERROR: {e}")
            print("\nFPLJoe may be blocking automated requests.")
            print("To work around this, save the page manually:")
            print("  1. Open https://www.fpljoe.com/?mode=world-cup in Chrome")
            print("  2. Press Cmd+S → save as 'fpljoe.html'")
            print("  3. Run: python fetch_team_odds.py --html-file fpljoe.html")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR fetching page: {e}")
            sys.exit(1)

    # Try parse strategies in order
    result = None

    next_data = _extract_next_data(html)
    if next_data:
        print("  Found Next.js __NEXT_DATA__, trying to parse …")
        result = _parse_next_data(next_data)
        if result:
            print(f"  Parsed {len(result[0])} teams from __NEXT_DATA__")

    if not result:
        print("  Trying inline JSON extraction …")
        result = _parse_inline_json(html)
        if result:
            print(f"  Parsed {len(result[0])} teams from inline JSON")

    if not result:
        print("  Trying HTML table parsing …")
        result = _parse_html_tables(html)
        if result:
            print(f"  Parsed {len(result[0])} teams from HTML table")

    if not result:
        print(
            "\nCould not automatically parse FPLJoe page.\n"
            "The site may require JavaScript rendering.\n\n"
            "Options:\n"
            "  1. Save page source after full load (Cmd+S) and use --html-file\n"
            "  2. Update data/team_stats.py manually with values from the site\n"
        )
        # Dump a snippet of the HTML for debugging
        snippet_path = Path("/tmp/fpljoe_debug.html")
        snippet_path.write_text(html[:50_000])
        print(f"  First 50 kB of HTML saved to {snippet_path} for inspection")
        sys.exit(1)

    proj_goals, cs_pct = result

    print(f"\nFound data for {len(proj_goals)} teams (PROJ_GOALS), {len(cs_pct)} teams (CS_PCT)")

    # Sanity check
    top = sorted(proj_goals.items(), key=lambda x: -sum(x[1]))[:5]
    print("Top 5 by avg xG:", [(k, [round(v,2) for v in vals]) for k, vals in top])

    _update_team_stats(proj_goals, cs_pct, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
