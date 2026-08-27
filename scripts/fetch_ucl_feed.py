#!/usr/bin/env python3
"""
Get the official UEFA Champions League Fantasy player pool (prices, positions,
clubs, ownership) into data/ucl_players.json — the UCL replacement for the FIFA
fantasy feed.

UEFA changes the feed path every season and rate-limits/blocks plain requests,
so there are three ways in, easiest last:

  1. Probe the known URL patterns (often fails on a new season):
        python3 scripts/fetch_ucl_feed.py

  2. Give it the exact URL you copied from DevTools:
        python3 scripts/fetch_ucl_feed.py --url "https://gaming.uefa.com/..."

  3. MOST RELIABLE — save the response from the browser, then parse it. In
     DevTools, right-click the players request -> Copy -> Copy as cURL, paste
     into the terminal and append  > raw.json , then:
        python3 scripts/fetch_ucl_feed.py --file raw.json
     Copy-as-cURL carries your real headers and cookies, so UEFA answers it.

Whatever the route, the script normalises the payload and prints the field
names it found, which is what's needed to wire the pool into data_engine.
"""
import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    requests = None

OUTPUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ucl_players.json"))

# Season "tour" ids change yearly; these are guesses for 2026-27. The DevTools
# route (--url / --file) is authoritative when they miss.
CANDIDATE_URLS = [
    "https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_90_en_1.json",
    "https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_80_en_1.json",
    "https://gaming.uefa.com/en/uclfantasy/services/feeds/players/players_70_en_1.json",
]

# Look like a real browser — a bare User-Agent gets stalled or dropped.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://gaming.uefa.com/en/uclfantasy",
    "Origin": "https://gaming.uefa.com",
    "Connection": "keep-alive",
}

# Keys that mark a dict as a player record in UEFA's feeds (any two will do).
_PLAYER_HINTS = {"id", "pdname", "playername", "name", "surname", "skill",
                 "value", "price", "tid", "teamid", "cteamid", "pos", "position",
                 "rating", "selected", "totalpoints", "islineup", "playerid"}


def find_player_list(node, depth: int = 0):
    """Walk an arbitrary JSON payload and return the biggest list that looks
    like player records. UEFA nests these differently each season, so search
    instead of hardcoding a path."""
    best = None
    if isinstance(node, list):
        dicts = [x for x in node if isinstance(x, dict)]
        if len(dicts) >= 10:
            keys = {k.lower() for d in dicts[:5] for k in d.keys()}
            if len(keys & _PLAYER_HINTS) >= 2:
                best = node
        for item in node[:50]:
            cand = find_player_list(item, depth + 1)
            if cand and (best is None or len(cand) > len(best)):
                best = cand
    elif isinstance(node, dict) and depth < 8:
        for val in node.values():
            cand = find_player_list(val, depth + 1)
            if cand and (best is None or len(cand) > len(best)):
                best = cand
    return best


def load_url(url: str, timeout: int):
    if requests is None:
        sys.exit("requests not installed: pip3 install requests")
    print(f"Trying {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
        return None
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}")
        return None
    ctype = r.headers.get("Content-Type", "")
    if "json" not in ctype.lower():
        print(f"  Got {ctype or 'unknown content-type'} — not JSON "
              f"(usually means the path is wrong or UEFA served a page).")
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"  Response was not parseable JSON: {e}")
        return None


def report(players: list) -> None:
    """Print the shape so the pool can be wired into data_engine without guessing."""
    sample = players[0]
    print(f"\nFound {len(players)} player records.")
    print("Field names:")
    for k in sorted(sample.keys()):
        v = sample[k]
        shown = v if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>"
        print(f"  {k:22s} = {shown!r}")
    # A couple of extra rows help disambiguate position/price encodings.
    if len(players) > 2:
        print("\nTwo more rows (to show how positions/prices vary):")
        for p in players[1:3]:
            print("  " + json.dumps(p, ensure_ascii=False)[:300])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Exact feed URL copied from browser DevTools")
    ap.add_argument("--file", help="Local JSON saved from the browser (Copy as cURL > raw.json)")
    ap.add_argument("--probe", action="store_true",
                    help="Try the guessed URL patterns (usually just hangs)")
    ap.add_argument("--timeout", type=int, default=45, help="Per-request timeout (default 45s)")
    ap.add_argument("--out", default=OUTPUT)
    args = ap.parse_args()

    if not (args.file or args.url or args.probe):
        print(__doc__.strip())
        print("\nNOTE: UEFA tarpits non-browser requests — every URL guess hangs for the\n"
              "full timeout even when the path is right, so probing is off by default.\n"
              "Use --file (recommended) or --url. Pass --probe to try the guesses anyway.")
        sys.exit(1)

    data = None
    if args.file:
        if not os.path.exists(args.file):
            sys.exit(f"No such file: {args.file}")
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {args.file}")
    else:
        for url in ([args.url] if args.url else CANDIDATE_URLS):
            data = load_url(url, args.timeout)
            if data:
                break

    if data is None:
        sys.exit(
            "\nNo feed retrieved.\n"
            "Most reliable route:\n"
            "  1. Open https://gaming.uefa.com/en/uclfantasy (logged in)\n"
            "  2. DevTools (Cmd+Opt+I) -> Network -> reload -> filter: players\n"
            "  3. Right-click the players request -> Copy -> Copy as cURL\n"
            "  4. Paste it in the terminal and append:  > raw.json\n"
            "  5. python3 scripts/fetch_ucl_feed.py --file raw.json\n"
        )

    players = find_player_list(data)
    if not players:
        # Still save it — the raw payload is useful for figuring out the shape.
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        sys.exit(f"Got JSON but found no player-like list. Saved raw payload to "
                 f"{args.out} — send it over and the parser can be adjusted.")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    report(players)
    print(f"\nSaved {len(players)} players -> {args.out}")


if __name__ == "__main__":
    main()
