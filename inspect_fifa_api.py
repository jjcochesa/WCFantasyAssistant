"""
Run this script locally (after logging into play.fifa.com) to discover
the exact FIFA Fantasy API endpoints and field names.

Usage:
  python inspect_fifa_api.py --token "Bearer eyJ..."
  python inspect_fifa_api.py  # tries without auth first
"""
import argparse, json, sys
import requests

CANDIDATE_URLS = [
    "https://gaming.fifa.com/api/en/fantasy/v2/players",
    "https://gaming.fifa.com/api/en/fantasy/v1/players",
    "https://gaming.fifa.com/api/en/fantasy/players",
    "https://play.fifa.com/json/fantasy/players.json",
    "https://play.fifa.com/fantasy/en/players",
    "https://play.fifa.com/fantasy/api/v2/players",
]

def probe(url, token=None):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if token:
        headers["Authorization"] = token
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"[{r.status_code}] {url}")
        if r.status_code == 200:
            data = r.json()
            print("  TOP-LEVEL KEYS:", list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]")
            items = data if isinstance(data, list) else (
                data.get("players") or data.get("data") or data.get("response") or []
            )
            if items:
                print("  FIRST PLAYER FIELDS:", list(items[0].keys()))
                print("  FIRST PLAYER SAMPLE:", json.dumps(items[0], indent=2)[:800])
            return True
    except Exception as e:
        print(f"[ERR] {url}: {e}")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=None, help="Bearer token from browser DevTools")
    args = parser.parse_args()
    found = False
    for url in CANDIDATE_URLS:
        if probe(url, args.token):
            found = True
            break
    if not found:
        print("\nNo endpoint found. Try logging into play.fifa.com, opening DevTools → Network,")
        print("filtering for 'fantasy', and copying the Authorization header. Then re-run with --token.")
