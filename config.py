import os
from dotenv import load_dotenv
load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
NATIONAL_TEAM_WEIGHT = 0.6
CLUB_FORM_WEIGHT = 0.4
FRIENDLY_FORM_WEIGHT = 0.30  # weight given to recent pre-WC friendlies vs season baseline

# Real World Cup form overlay (data/wc_stats.json, refreshed each round from API-Football).
# Weight ramps with WC minutes played: wc_weight = min(MAX, wc_minutes / FULL_TRUST_MIN).
WC_FORM_MAX_WEIGHT     = 0.60   # cap — most WC form can override the baseline
WC_FORM_FULL_TRUST_MIN = 270.0  # minutes (≈3 full matches) for weight to hit the cap
WC_FORM_MIN_MINUTES    = 20     # minimum WC minutes before the overlay applies at all
