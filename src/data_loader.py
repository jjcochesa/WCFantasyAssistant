"""
Orchestrates fetching and enriching players with stats from API-Football.
Combines FIFA Fantasy prices/ownership with real match statistics.
"""

import os
from typing import Optional
import pandas as pd

from src.api.models import Player, PlayerStats
from src.api.fifa_fantasy import fetch_players, load_players_from_file
from src.api.api_football import (
    get_player_stats_national,
    get_player_stats_club,
    get_all_teams_wc2026,
)
from src.analysis.ranker import rank_players
from config import WC_2026_LEAGUE_ID, WC_2026_SEASON, QUALIFYING_SEASON, CACHE_DIR


def load_and_enrich(
    fifa_session_token: Optional[str] = None,
    players_file: Optional[str] = None,
    use_demo_data: bool = False,
) -> pd.DataFrame:
    """
    Main pipeline:
    1. Load players from FIFA Fantasy (prices, ownership)
    2. Enrich with national team stats from API-Football
    3. Enrich with club stats from API-Football
    4. Score and rank all players
    Returns a ranked DataFrame.
    """
    if use_demo_data:
        players = _generate_demo_players()
    elif players_file and os.path.exists(players_file):
        players = load_players_from_file(players_file)
    else:
        players = fetch_players(session_token=fifa_session_token)

    if not use_demo_data and os.getenv("API_FOOTBALL_KEY"):
        _enrich_with_stats(players)

    return rank_players(players)


def _enrich_with_stats(players: list[Player]) -> None:
    """Fetch and attach real stats from API-Football (slow — uses API quota)."""
    print(f"Enriching {len(players)} players with API-Football stats...")
    for i, player in enumerate(players):
        try:
            if player.team_country_id:
                nat_stats = get_player_stats_national(
                    int(player.id), player.team_country_id
                )
                if nat_stats:
                    player.national_stats = nat_stats

            if player.club_id:
                club_stats = get_player_stats_club(
                    int(player.id), player.club_id, season=QUALIFYING_SEASON
                )
                if club_stats:
                    player.club_stats = club_stats

            if (i + 1) % 20 == 0:
                print(f"  Processed {i + 1}/{len(players)}...")
        except Exception as e:
            print(f"  Skipping {player.name}: {e}")


def _generate_demo_players() -> list[Player]:
    """
    Hardcoded demo dataset of top World Cup 2026 players.
    Used when no API key is available — covers all 4 positions with realistic stats.
    """
    demo = [
        # ── GOALKEEPERS ──────────────────────────────────────────────────────
        Player("1", "Thibaut Courtois", "GK", "Belgium", price=6.0, ownership_pct=18.0,
               club="Real Madrid", club_id=541,
               national_stats=PlayerStats(matches=10, minutes=900, goals=0, assists=0,
                   clean_sheets=6, saves=35, goals_conceded=8, yellow_cards=0),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=0, assists=0,
                   clean_sheets=12, saves=90, goals_conceded=22, yellow_cards=1)),

        Player("2", "Alisson Becker", "GK", "Brazil", price=5.5, ownership_pct=14.0,
               club="Liverpool", club_id=40,
               national_stats=PlayerStats(matches=10, minutes=900, goals=0, assists=0,
                   clean_sheets=7, saves=28, goals_conceded=6, yellow_cards=0),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=0, assists=0,
                   clean_sheets=14, saves=85, goals_conceded=28, yellow_cards=0)),

        Player("3", "Emiliano Martinez", "GK", "Argentina", price=5.5, ownership_pct=12.0,
               club="Aston Villa", club_id=66,
               national_stats=PlayerStats(matches=10, minutes=900, goals=0, assists=0,
                   clean_sheets=6, saves=30, goals_conceded=9, yellow_cards=1),
               club_stats=PlayerStats(matches=33, minutes=2970, goals=0, assists=0,
                   clean_sheets=11, saves=95, goals_conceded=38, yellow_cards=2)),

        Player("4", "Yann Sommer", "GK", "Switzerland", price=4.5, ownership_pct=4.0,
               club="Inter Milan", club_id=505,
               national_stats=PlayerStats(matches=8, minutes=720, goals=0, assists=0,
                   clean_sheets=4, saves=22, goals_conceded=10, yellow_cards=0),
               club_stats=PlayerStats(matches=31, minutes=2790, goals=0, assists=0,
                   clean_sheets=15, saves=78, goals_conceded=23, yellow_cards=0)),

        # ── DEFENDERS ────────────────────────────────────────────────────────
        Player("10", "Virgil van Dijk", "DEF", "Netherlands", price=7.0, ownership_pct=22.0,
               club="Liverpool", club_id=40,
               national_stats=PlayerStats(matches=10, minutes=900, goals=2, assists=1,
                   clean_sheets=6, goals_conceded=9, tackles=20, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=3, assists=2,
                   clean_sheets=14, goals_conceded=28, tackles=55, yellow_cards=2)),

        Player("11", "Achraf Hakimi", "DEF", "Morocco", price=7.5, ownership_pct=28.0,
               club="PSG", club_id=85,
               national_stats=PlayerStats(matches=10, minutes=900, goals=3, assists=4,
                   clean_sheets=5, goals_conceded=8, tackles=22, yellow_cards=2),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=5, assists=8,
                   clean_sheets=10, goals_conceded=25, tackles=60, yellow_cards=3)),

        Player("12", "Alejandro Grimaldo", "DEF", "Spain", price=7.0, ownership_pct=25.0,
               club="Bayer Leverkusen", club_id=168,
               national_stats=PlayerStats(matches=9, minutes=810, goals=2, assists=3,
                   clean_sheets=5, goals_conceded=7, tackles=18, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=6, assists=12,
                   clean_sheets=11, goals_conceded=20, tackles=55, yellow_cards=2)),

        Player("13", "Theo Hernandez", "DEF", "France", price=7.5, ownership_pct=20.0,
               club="AC Milan", club_id=489,
               national_stats=PlayerStats(matches=8, minutes=720, goals=2, assists=2,
                   clean_sheets=4, goals_conceded=6, tackles=15, yellow_cards=2),
               club_stats=PlayerStats(matches=28, minutes=2520, goals=4, assists=7,
                   clean_sheets=9, goals_conceded=22, tackles=48, yellow_cards=4)),

        Player("14", "Joao Cancelo", "DEF", "Portugal", price=6.5, ownership_pct=15.0,
               club="FC Barcelona", club_id=529,
               national_stats=PlayerStats(matches=9, minutes=810, goals=1, assists=3,
                   clean_sheets=5, goals_conceded=8, tackles=20, yellow_cards=2),
               club_stats=PlayerStats(matches=26, minutes=2340, goals=2, assists=5,
                   clean_sheets=8, goals_conceded=20, tackles=52, yellow_cards=3)),

        Player("15", "William Saliba", "DEF", "France", price=6.0, ownership_pct=10.0,
               club="Arsenal", club_id=42,
               national_stats=PlayerStats(matches=9, minutes=810, goals=1, assists=0,
                   clean_sheets=5, goals_conceded=7, tackles=25, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=2, assists=1,
                   clean_sheets=14, goals_conceded=22, tackles=70, yellow_cards=2)),

        Player("16", "Nuno Mendes", "DEF", "Portugal", price=6.0, ownership_pct=8.0,
               club="PSG", club_id=85,
               national_stats=PlayerStats(matches=9, minutes=810, goals=1, assists=2,
                   clean_sheets=5, goals_conceded=8, tackles=18, yellow_cards=1),
               club_stats=PlayerStats(matches=27, minutes=2430, goals=1, assists=4,
                   clean_sheets=9, goals_conceded=20, tackles=48, yellow_cards=2)),

        Player("17", "Ruben Dias", "DEF", "Portugal", price=6.5, ownership_pct=9.0,
               club="Manchester City", club_id=50,
               national_stats=PlayerStats(matches=9, minutes=810, goals=1, assists=0,
                   clean_sheets=6, goals_conceded=7, tackles=22, yellow_cards=2),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=1, assists=1,
                   clean_sheets=13, goals_conceded=24, tackles=62, yellow_cards=2)),

        Player("18", "Alessandro Bastoni", "DEF", "Italy", price=6.0, ownership_pct=4.5,
               club="Inter Milan", club_id=505,
               national_stats=PlayerStats(matches=9, minutes=810, goals=1, assists=1,
                   clean_sheets=4, goals_conceded=10, tackles=28, yellow_cards=2),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=2, assists=3,
                   clean_sheets=13, goals_conceded=25, tackles=75, yellow_cards=3)),

        # ── MIDFIELDERS ──────────────────────────────────────────────────────
        Player("30", "Pedri", "MID", "Spain", price=8.5, ownership_pct=30.0,
               club="FC Barcelona", club_id=529,
               national_stats=PlayerStats(matches=10, minutes=900, goals=3, assists=5,
                   chances_created=22, tackles=18, yellow_cards=1),
               club_stats=PlayerStats(matches=28, minutes=2520, goals=6, assists=8,
                   chances_created=55, tackles=40, yellow_cards=3)),

        Player("31", "Jude Bellingham", "MID", "England", price=9.5, ownership_pct=45.0,
               club="Real Madrid", club_id=541,
               national_stats=PlayerStats(matches=10, minutes=900, goals=5, assists=3,
                   chances_created=18, tackles=15, yellow_cards=2),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=19, assists=10,
                   chances_created=48, tackles=38, yellow_cards=4)),

        Player("32", "Phil Foden", "MID", "England", price=8.5, ownership_pct=25.0,
               club="Manchester City", club_id=50,
               national_stats=PlayerStats(matches=9, minutes=810, goals=4, assists=3,
                   chances_created=20, tackles=8, yellow_cards=0),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=14, assists=11,
                   chances_created=58, tackles=18, yellow_cards=2)),

        Player("33", "Florian Wirtz", "MID", "Germany", price=9.0, ownership_pct=35.0,
               club="Bayer Leverkusen", club_id=168,
               national_stats=PlayerStats(matches=10, minutes=900, goals=4, assists=6,
                   chances_created=25, tackles=10, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=12, assists=14,
                   chances_created=70, tackles=22, yellow_cards=2)),

        Player("34", "Vitinha", "MID", "Portugal", price=7.5, ownership_pct=12.0,
               club="PSG", club_id=85,
               national_stats=PlayerStats(matches=10, minutes=900, goals=2, assists=4,
                   chances_created=20, tackles=22, yellow_cards=1),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=4, assists=8,
                   chances_created=52, tackles=55, yellow_cards=3)),

        Player("35", "Granit Xhaka", "MID", "Switzerland", price=6.5, ownership_pct=4.0,
               club="Bayer Leverkusen", club_id=168,
               national_stats=PlayerStats(matches=10, minutes=900, goals=2, assists=3,
                   chances_created=16, tackles=28, yellow_cards=3),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=3, assists=5,
                   chances_created=38, tackles=72, yellow_cards=5)),

        Player("36", "Declan Rice", "MID", "England", price=7.5, ownership_pct=20.0,
               club="Arsenal", club_id=42,
               national_stats=PlayerStats(matches=10, minutes=900, goals=2, assists=2,
                   chances_created=14, tackles=30, yellow_cards=2),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=7, assists=8,
                   chances_created=45, tackles=82, yellow_cards=4)),

        Player("37", "Luka Modric", "MID", "Croatia", price=6.5, ownership_pct=8.0,
               club="Real Madrid", club_id=541,
               national_stats=PlayerStats(matches=8, minutes=720, goals=1, assists=3,
                   chances_created=18, tackles=20, yellow_cards=1),
               club_stats=PlayerStats(matches=22, minutes=1980, goals=3, assists=6,
                   chances_created=40, tackles=35, yellow_cards=2)),

        Player("38", "Alexis Mac Allister", "MID", "Argentina", price=7.5, ownership_pct=18.0,
               club="Liverpool", club_id=40,
               national_stats=PlayerStats(matches=10, minutes=900, goals=3, assists=3,
                   chances_created=16, tackles=25, yellow_cards=2),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=6, assists=7,
                   chances_created=42, tackles=60, yellow_cards=3)),

        Player("39", "Nico Williams", "MID", "Spain", price=7.5, ownership_pct=22.0,
               club="Athletic Bilbao", club_id=531,
               national_stats=PlayerStats(matches=10, minutes=900, goals=3, assists=5,
                   chances_created=24, tackles=12, yellow_cards=1),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=10, assists=12,
                   chances_created=60, tackles=28, yellow_cards=2)),

        # ── FORWARDS ─────────────────────────────────────────────────────────
        Player("50", "Kylian Mbappe", "FWD", "France", price=12.0, ownership_pct=60.0,
               club="Real Madrid", club_id=541,
               national_stats=PlayerStats(matches=10, minutes=900, goals=8, assists=3,
                   shots_on_target=28, yellow_cards=1),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=25, assists=8,
                   shots_on_target=80, yellow_cards=2)),

        Player("51", "Erling Haaland", "FWD", "Norway", price=11.5, ownership_pct=40.0,
               club="Manchester City", club_id=50,
               national_stats=PlayerStats(matches=8, minutes=720, goals=7, assists=2,
                   shots_on_target=22, yellow_cards=1),
               club_stats=PlayerStats(matches=26, minutes=2340, goals=22, assists=5,
                   shots_on_target=72, yellow_cards=1)),

        Player("52", "Vinicius Jr", "FWD", "Brazil", price=11.0, ownership_pct=45.0,
               club="Real Madrid", club_id=541,
               national_stats=PlayerStats(matches=10, minutes=900, goals=6, assists=4,
                   shots_on_target=25, yellow_cards=2),
               club_stats=PlayerStats(matches=28, minutes=2520, goals=18, assists=9,
                   shots_on_target=68, yellow_cards=4)),

        Player("53", "Harry Kane", "FWD", "England", price=10.5, ownership_pct=35.0,
               club="Bayern Munich", club_id=157,
               national_stats=PlayerStats(matches=10, minutes=900, goals=7, assists=3,
                   shots_on_target=24, yellow_cards=0),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=30, assists=8,
                   shots_on_target=88, yellow_cards=1)),

        Player("54", "Lamine Yamal", "FWD", "Spain", price=10.5, ownership_pct=38.0,
               club="FC Barcelona", club_id=529,
               national_stats=PlayerStats(matches=10, minutes=900, goals=5, assists=6,
                   shots_on_target=20, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=14, assists=15,
                   shots_on_target=62, yellow_cards=2)),

        Player("55", "Bukayo Saka", "FWD", "England", price=9.5, ownership_pct=28.0,
               club="Arsenal", club_id=42,
               national_stats=PlayerStats(matches=10, minutes=900, goals=4, assists=5,
                   shots_on_target=18, yellow_cards=1),
               club_stats=PlayerStats(matches=32, minutes=2880, goals=16, assists=14,
                   shots_on_target=58, yellow_cards=2)),

        Player("56", "Memphis Depay", "FWD", "Netherlands", price=7.5, ownership_pct=4.5,
               club="Atletico Madrid", club_id=530,
               national_stats=PlayerStats(matches=9, minutes=810, goals=5, assists=2,
                   shots_on_target=18, yellow_cards=1),
               club_stats=PlayerStats(matches=25, minutes=2250, goals=12, assists=4,
                   shots_on_target=48, yellow_cards=3)),

        Player("57", "Robert Lewandowski", "FWD", "Poland", price=9.0, ownership_pct=15.0,
               club="FC Barcelona", club_id=529,
               national_stats=PlayerStats(matches=10, minutes=900, goals=6, assists=2,
                   shots_on_target=22, yellow_cards=1),
               club_stats=PlayerStats(matches=30, minutes=2700, goals=20, assists=6,
                   shots_on_target=70, yellow_cards=2)),

        Player("58", "Richarlison", "FWD", "Brazil", price=7.5, ownership_pct=4.2,
               club="Tottenham", club_id=47,
               national_stats=PlayerStats(matches=9, minutes=810, goals=5, assists=2,
                   shots_on_target=20, yellow_cards=1),
               club_stats=PlayerStats(matches=22, minutes=1980, goals=10, assists=3,
                   shots_on_target=42, yellow_cards=2)),
    ]
    return demo
