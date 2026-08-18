#!/usr/bin/env bash
#
# UCL matchday refresh — run on your Mac after a matchday finishes.
#
#   cd ~/UCLFantasyAssistant
#   git pull origin <branch>
#   ./scripts/matchday_refresh.sh YOUR_API_FOOTBALL_KEY [FROM_MD]
#
# FROM_MD = first league matchday still to be played (default 1). Pass e.g. 5
# after MD4 has finished so the league-phase sim only rolls the remaining games.
#
# Step 1  Accumulated per-player UCL stats  -> data/ucl_stats.json
#         (--refresh re-pulls every finished fixture so any game cached before
#         the API finished updating minutes gets corrected)
# Step 2  Current club Elo ratings          -> data/ucl_elo.csv
# Step 3  League-phase + knockout Monte-Carlo -> data/ucl_league_output.json
#
# Nothing here edits data/team_stats.py or commits — you review the outputs
# (or send them to Claude) and we wire them in together.

set -euo pipefail

KEY="${1:-}"
FROM_MD="${2:-1}"
if [ -z "$KEY" ]; then
  echo "Usage: ./scripts/matchday_refresh.sh YOUR_API_FOOTBALL_KEY [FROM_MD]"
  exit 1
fi

cd "$(dirname "$0")/.."

echo "============================================================"
echo " 1/3  UCL player stats so far  (data/ucl_stats.json)"
echo "============================================================"
python3 scripts/fetch_wc_stats.py --key "$KEY" --league 2 --season 2026 --refresh

echo
echo "============================================================"
echo " 2/3  Club Elo ratings  (data/ucl_elo.csv)"
echo "============================================================"
python3 scripts/fetch_clubelo.py

echo
echo "============================================================"
echo " 3/3  League phase + knockout sim from MD${FROM_MD}"
echo "============================================================"
if [ -f data/ucl_fixtures.json ]; then
  STANDINGS_ARG=""
  [ -f data/ucl_standings.json ] && STANDINGS_ARG="--standings data/ucl_standings.json"
  # shellcheck disable=SC2086
  python3 scripts/build_league_phase.py \
      --elo data/ucl_elo.csv --from-md "$FROM_MD" $STANDINGS_ARG
else
  echo "  Skipped: data/ucl_fixtures.json not present yet (needs the draw)."
fi

echo
echo "============================================================"
echo " Done. Review / send to Claude:"
echo "   - data/ucl_stats.json          (player stats so far)"
echo "   - data/ucl_league_output.json  (reach probs + expected games)"
echo "============================================================"
