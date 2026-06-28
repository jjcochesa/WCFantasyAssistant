#!/usr/bin/env bash
#
# Sunday R32 refresh — one command, one API key. Run on your Mac after MD3 ends.
#
#   cd ~/WCFantasyAssistant
#   git pull origin claude/vibrant-davinci-JojAL
#   ./scripts/sunday_refresh.sh YOUR_API_FOOTBALL_KEY
#
# Step 1 pulls every player's accumulated WC stats THROUGH MD3 (--refresh re-pulls
#        all finished fixtures so any stale-at-final-whistle games get corrected),
#        and writes data/wc_stats.json — the projection model picks these up.
# Step 2 builds the R32 team pack (goals / CS% / FDR) from odds + the Monte-Carlo
#        advancement probabilities, and writes data/r32_output.json.
#
# Neither step edits data/team_stats.py or commits anything — you review the two
# output files (or send them to Claude) and we wire them in together.

set -euo pipefail

KEY="${1:-}"
if [ -z "$KEY" ]; then
  echo "Usage: ./scripts/sunday_refresh.sh YOUR_API_FOOTBALL_KEY"
  exit 1
fi

cd "$(dirname "$0")/.."

echo "============================================================"
echo " 1/2  MD3 player stats  (data/wc_stats.json)"
echo "============================================================"
python3 scripts/fetch_wc_stats.py --key "$KEY" --refresh

echo
echo "============================================================"
echo " 2/2  R32 team data + advancement  (data/r32_output.json)"
echo "============================================================"
python3 scripts/build_r32.py --key "$KEY" --elo-file data/elo_ratings.csv

echo
echo "============================================================"
echo " Done. Review / send to Claude:"
echo "   - data/wc_stats.json     (MD3 player stats)"
echo "   - data/r32_output.json   (R32 goals/CS%/FDR + qual %)"
echo "============================================================"
