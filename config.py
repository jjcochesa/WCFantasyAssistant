import os
from dotenv import load_dotenv
load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
NATIONAL_TEAM_WEIGHT = 0.6
CLUB_FORM_WEIGHT = 0.4
FRIENDLY_FORM_WEIGHT = 0.30  # weight given to recent pre-WC friendlies vs season baseline

# Real World Cup form overlay (data/wc_stats.json, refreshed each round from API-Football).
# Empirical-Bayes (Gamma-Poisson) posterior: the player's WC counts are shrunk toward
# their own pre-tournament per-90 baseline, which acts as the prior.
#   posterior_per90 = (baseline_per90 * PRIOR_GAMES + wc_count) / (PRIOR_GAMES + wc_90s)
# One quiet/explosive match barely moves the estimate; as WC minutes accumulate the
# observed rate takes over automatically (no weight cap needed).
WC_FORM_PRIOR_GAMES = 3.0    # prior strength, in 90-min games, on the baseline
WC_FORM_MIN_MINUTES = 20     # minimum WC minutes before the overlay applies at all

# WC minutes also drive the next round's minutes projection (recent minutes predict the
# lineup far better than a frozen pre-tournament XI). Lower = trust recent minutes faster.
WC_MINUTES_PRIOR_GAMES = 0.5
