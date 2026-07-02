#!/usr/bin/env bash
#
# Knockout refresh — one command, one API key. Run on your Mac after a round ends.
#
#   cd ~/WCFantasyAssistant
#   git pull origin claude/vibrant-davinci-JojAL
#   ./scripts/sunday_refresh.sh YOUR_API_FOOTBALL_KEY ["Round of 16"]
#
# Second arg = the round to build (default "Round of 16"). Use the exact
# API-Football round name: "Round of 32", "Round of 16", "Quarter-finals",
# "Semi-finals", "Final".
#
# Step 1 re-pulls every player's accumulated WC stats so far (--refresh corrects
#        any games cached before the API finished updating) → data/wc_stats.json.
# Step 2 builds the team pack (goals / CS% / FDR) from odds + the Monte-Carlo
#        advancement probabilities → data/r32_output.json.
#
# Neither step edits data/team_stats.py or commits anything — you review the two
# output files (or send them to Claude) and we wire them in together.

set -euo pipefail

KEY="${1:-}"
ROUND="${2:-Round of 16}"
if [ -z "$KEY" ]; then
  echo "Usage: ./scripts/sunday_refresh.sh YOUR_API_FOOTBALL_KEY [\"Round of 16\"]"
  exit 1
fi

cd "$(dirname "$0")/.."

echo "============================================================"
echo " 1/2  Player stats so far  (data/wc_stats.json)"
echo "============================================================"
python3 scripts/fetch_wc_stats.py --key "$KEY" --refresh

echo
echo "============================================================"
echo " 2/2  ${ROUND} team data + advancement  (data/r32_output.json)"
echo "============================================================"
python3 scripts/build_r32.py --key "$KEY" --round "$ROUND" --elo-file data/elo_ratings.csv

echo
echo "============================================================"
echo " Done. Review / send to Claude:"
echo "   - data/wc_stats.json     (player stats so far)"
echo "   - data/r32_output.json   (${ROUND} goals/CS%/FDR + qual %)"
echo "============================================================"
