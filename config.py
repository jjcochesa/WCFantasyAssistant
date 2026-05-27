import os
from dotenv import load_dotenv

load_dotenv()

# API-Football (api-sports.io) — get free key at https://dashboard.api-football.com/
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

# World Cup 2026 identifiers on API-Football
WC_2026_LEAGUE_ID = 1
WC_2026_SEASON = 2026

# Qualifying leagues season (recent club form)
QUALIFYING_SEASON = 2024  # 2024/25 season

# Cache directory
CACHE_DIR = "data/cache"

# Stats weighting for combined score
NATIONAL_TEAM_WEIGHT = 0.6
CLUB_FORM_WEIGHT = 0.4

# Low-ownership differential threshold
LOW_OWNERSHIP_THRESHOLD = 5.0  # %
LOW_OWNERSHIP_BONUS = 2  # extra points when >4pts scored

# Recent form window (number of matches)
RECENT_FORM_MATCHES = 10
