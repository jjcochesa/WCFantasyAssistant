from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerStats:
    """Per-match or aggregated stats for a player."""
    matches: int = 0
    minutes: int = 0
    goals: int = 0
    assists: int = 0
    shots_on_target: float = 0.0
    chances_created: float = 0.0
    tackles: float = 0.0
    clean_sheets: int = 0         # matches with clean sheet (GK/DEF)
    saves: float = 0.0            # GK saves
    yellow_cards: int = 0
    red_cards: int = 0
    goals_conceded: int = 0       # GK/DEF
    penalties_saved: int = 0      # GK
    penalties_missed: int = 0
    own_goals: int = 0

    def per_90(self, stat: float) -> float:
        mins = max(self.minutes, 1)
        return stat / mins * 90


@dataclass
class Player:
    """A player in the FIFA WC Fantasy game."""
    id: str
    name: str
    position: str          # GK / DEF / MID / FWD
    team_country: str      # National team (e.g. "Brazil")
    team_country_id: Optional[int] = None
    club: str = ""
    club_id: Optional[int] = None
    price: float = 0.0            # in millions
    ownership_pct: float = 0.0    # % of teams who own this player

    # Stats contexts
    national_stats: PlayerStats = field(default_factory=PlayerStats)
    club_stats: PlayerStats = field(default_factory=PlayerStats)

    # Computed scores (filled by ranker)
    national_xpts_per_match: float = 0.0
    club_xpts_per_match: float = 0.0
    combined_xpts_per_match: float = 0.0
    value_score: float = 0.0          # xPts / price
    differential_score: float = 0.0   # weighted by low-ownership bonus

    @property
    def is_differential(self) -> bool:
        return self.ownership_pct < 5.0

    @property
    def display_price(self) -> str:
        return f"${self.price:.1f}m"
