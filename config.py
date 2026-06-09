import os
from dotenv import load_dotenv
load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
NATIONAL_TEAM_WEIGHT = 0.6
CLUB_FORM_WEIGHT = 0.4
FRIENDLY_FORM_WEIGHT = 0.30  # weight given to recent pre-WC friendlies vs season baseline
