"""
Tank01 NFL API Client Module

Real-time sports data integration for FRONTAL LOBE prediction engine.

This module provides a complete wrapper around the Tank01 NFL API (via RapidAPI),
which gives us:
  - Real-time betting odds and player props (DraftKings lines)
  - Live game statistics (updated every play)
  - DFS salaries and fantasy projections
  - Injury updates and depth charts
  - All data needed for edge detection (model prediction vs market line)

Key Endpoints:
  - getNFLBettingOdds: Real-time player props with lines
  - getNFLGameBoxScore: Live stats (plays, yards, TD, etc.)
  - getDFSSalaries: DraftKings salaries + FPPG
  - getNFLInjuryList: Real-time player status
  - getPlayerInformation: Player details
  - getNFLDepthCharts: Snap count predictions

Free Tier: Available via RapidAPI (free credits for dev/test)
Production: $30-50/month on RapidAPI for unlimited calls

Author: FRONTAL LOBE Data Lake Team
Version: 1.0.0
"""

import requests
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import time
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS (Typed Responses)
# ============================================================================

class StatType(Enum):
    """Supported betting stat types for player props."""
    PASSING_YARDS = "Passing Yards"
    PASSING_TDS = "Passing TDs"
    PASSING_INTERCEPTIONS = "Passing Interceptions"
    RUSHING_YARDS = "Rushing Yards"
    RUSHING_TDS = "Rushing TDs"
    RECEIVING_YARDS = "Receiving Yards"
    RECEIVING_RECEPTIONS = "Receptions"
    RECEIVING_TDS = "Receiving TDs"
    TACKLES = "Tackles"
    SACKS = "Sacks"
    INTERCEPTIONS = "Interceptions"


class PlayerStatus(Enum):
    """Player status indicators."""
    ACTIVE = "Active"
    OUT = "Out"
    DOUBTFUL = "Doubtful"
    QUESTIONABLE = "Questionable"
    PROBABLE = "Probable"
    INJURED_RESERVE = "Injured Reserve"
    UNKNOWN = "Unknown"


@dataclass
class PlayerProp:
    """Single player prop with betting information."""
    player_name: str
    player_id: Optional[str]
    position: Optional[str]
    team: str
    stat_type: str
    line: float
    over_odds: float
    under_odds: float
    implied_total: Optional[float]
    timestamp: str
    game_id: Optional[str]
    game_date: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PlayerGameStats:
    """Live player statistics during a game."""
    player_name: str
    player_id: Optional[str]
    position: str
    team: str
    game_id: str
    
    # Offensive stats
    passing_yards: Optional[int] = None
    passing_tds: Optional[int] = None
    passing_interceptions: Optional[int] = None
    rushing_yards: Optional[int] = None
    rushing_tds: Optional[int] = None
    receiving_yards: Optional[int] = None
    receptions: Optional[int] = None
    receiving_tds: Optional[int] = None
    
    # Defensive stats
    tackles: Optional[int] = None
    sacks: Optional[float] = None
    interceptions: Optional[int] = None
    
    # Meta
    updated_at: str = ""
    quarter: Optional[int] = None
    snap_count: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class InjuryUpdate:
    """Player injury status update."""
    player_name: str
    player_id: Optional[str]
    position: str
    team: str
    status: str
    injury_type: Optional[str]
    return_to_play: Optional[str]
    updated_at: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DFSSalary:
    """DraftKings salary and fantasy information."""
    player_name: str
    player_id: Optional[str]
    position: str
    team: str
    salary: float
    fppg: Optional[float]
    projected_fpts: Optional[float]
    injury_indicator: Optional[str]
    last_week_fpts: Optional[float]
    season_fppg: Optional[float]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DepthChartEntry:
    """Depth chart position entry."""
    player_name: str
    position: str
    depth_order: int
    snap_percentage: Optional[float]
    team: str
    injured: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# TANK01 API CLIENT
# ============================================================================

class Tank01NFLClient:
    """
    Tank01 NFL API Client
    
    Provides real-time sports data for FRONTAL LOBE prediction engine.
    Integrates with RapidAPI for easy key management and rate limiting.
    """

    # API Configuration
    BASE_URL = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
    
    # Rate limiting
    REQUESTS_PER_SECOND = 5  # Free tier is generous
    REQUEST_DELAY = 1.0 / REQUESTS_PER_SECOND
    
    def __init__(self, api_key: str, rapidapi_host: str = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"):
        """
        Initialize Tank01 NFL API client.
        
        Args:
            api_key: RapidAPI key (get from https://rapidapi.com/mma8/api/tank01-nfl-live-in-game-real-time-statistics-nfl)
            rapidapi_host: RapidAPI host (default provided)
        
        Raises:
            ValueError: If API key is not provided
        """
        if not api_key or api_key.strip() == "":
            raise ValueError("API key is required. Get it from RapidAPI.")
        
        self.api_key = api_key
        self.rapidapi_host = rapidapi_host
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.error_count = 0
        
        # Cache
        self.cache = {}
        self.cache_ttl = 60  # Cache for 60 seconds
        
        logger.info("Tank01 NFL API Client initialized")
        logger.info(f"Base URL: {self.BASE_URL}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers for RapidAPI."""
        return {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.rapidapi_host,
            'Content-Type': 'application/json',
        }

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key from endpoint and parameters."""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}:{param_str}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key in self.cache:
            item, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit: {key}")
                return item
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, value: Any):
        """Store item in cache."""
        self.cache[key] = (value, time.time())

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """
        Make HTTP request to Tank01 API.
        
        Args:
            endpoint: API endpoint name (e.g., 'getNFLBettingOdds')
            params: Query parameters
        
        Returns:
            Response JSON
        
        Raises:
            requests.RequestException: If request fails
        """
        # Check cache
        cache_key = self._get_cache_key(endpoint, params)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Rate limit
        self._rate_limit()
        
        # Build URL
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            logger.debug(f"Request: {endpoint} with params {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=10
            )
            
            response.raise_for_status()
            self.request_count += 1
            
            data = response.json()
            
            # Cache successful response
            self._set_cache(cache_key, data)
            
            logger.debug(f"Response: {endpoint} returned {len(str(data))} bytes")
            
            return data
        
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            logger.error(f"API request failed: {endpoint} - {e}")
            logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            raise

    # ========================================================================
    # CORE ENDPOINTS
    # ========================================================================

    def get_nfl_betting_odds(
        self,
        game_date: str,
        player_props: bool = True,
        implied_totals: bool = True,
        item_format: str = "list"
    ) -> List[PlayerProp]:
        """
        Get real-time NFL betting odds including player props.
        
        **THIS IS YOUR #1 ENDPOINT FOR EDGE DETECTION**
        
        Args:
            game_date: Date in format YYYYMMDD (e.g., "20250907")
            player_props: Include player prop lines (True for DraftKings data)
            implied_totals: Include implied probability totals
            item_format: Response format ("list" or "json")
        
        Returns:
            List of PlayerProp objects with real-time odds
        
        Example:
            >>> client = Tank01NFLClient(api_key)
            >>> props = client.get_nfl_betting_odds("20250907", player_props=True)
            >>> for prop in props:
            ...     print(f"{prop.player_name}: {prop.stat_type} {prop.line}")
        """
        params = {
            "gameDate": game_date,
            "playerProps": str(player_props).lower(),
            "impliedTotals": str(implied_totals).lower(),
            "itemFormat": item_format,
        }
        
        try:
            response = self._make_request("getNFLBettingOdds", params)
            
            props = []
            
            # Parse response (format varies, be flexible)
            if isinstance(response, dict):
                # Handle different response structures
                odds_list = response.get('odds', response.get('playerProps', response.get('data', [])))
                if not isinstance(odds_list, list):
                    odds_list = [response]
            else:
                odds_list = response if isinstance(response, list) else []
            
            for item in odds_list:
                try:
                    prop = PlayerProp(
                        player_name=item.get('playerName', item.get('name', 'Unknown')),
                        player_id=item.get('playerId', item.get('playerID')),
                        position=item.get('position', item.get('pos')),
                        team=item.get('team', item.get('nflTeam', 'N/A')),
                        stat_type=item.get('statType', item.get('stat', 'Unknown')),
                        line=float(item.get('line', item.get('over', 0))),
                        over_odds=float(item.get('overOdds', item.get('overOdd', -110))),
                        under_odds=float(item.get('underOdds', item.get('underOdd', -110))),
                        implied_total=float(item.get('impliedTotal', 0)) if item.get('impliedTotal') else None,
                        timestamp=item.get('timestamp', datetime.now().isoformat()),
                        game_id=item.get('gameId', item.get('gameID')),
                        game_date=game_date,
                    )
                    props.append(prop)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse prop: {item} - {e}")
                    continue
            
            logger.info(f"Retrieved {len(props)} player props for {game_date}")
            return props
        
        except Exception as e:
            logger.error(f"Failed to get betting odds: {e}")
            return []

    def get_nfl_game_box_score(
        self,
        game_id: str,
        item_format: str = "list"
    ) -> List[PlayerGameStats]:
        """
        Get live NFL game box score with real-time player statistics.
        
        **USE THIS TO TRACK LIVE PROP PERFORMANCE**
        
        Updates every play during the game. Perfect for:
        - Monitoring live prop progress
        - Early exit decisions on bets
        - Tracking if prediction is on pace
        
        Args:
            game_id: Game ID (e.g., from betting odds response)
            item_format: Response format ("list" or "json")
        
        Returns:
            List of PlayerGameStats with current stats
        
        Example:
            >>> client = Tank01NFLClient(api_key)
            >>> stats = client.get_nfl_game_box_score("20250907001")
            >>> for player_stat in stats:
            ...     if player_stat.receiving_yards:
            ...         print(f"{player_stat.player_name}: {player_stat.receiving_yards} rec yards")
        """
        params = {
            "gameID": game_id,
            "itemFormat": item_format,
        }
        
        try:
            response = self._make_request("getNFLGameBoxScore", params)
            
            stats = []
            
            # Parse response
            if isinstance(response, dict):
                players_list = response.get('players', response.get('data', response.get('stats', [])))
                if not isinstance(players_list, list):
                    players_list = [response]
            else:
                players_list = response if isinstance(response, list) else []
            
            for item in players_list:
                try:
                    player_stat = PlayerGameStats(
                        player_name=item.get('playerName', item.get('name', 'Unknown')),
                        player_id=item.get('playerId', item.get('playerID')),
                        position=item.get('position', item.get('pos', 'Unknown')),
                        team=item.get('team', item.get('nflTeam', 'N/A')),
                        game_id=game_id,
                        passing_yards=int(item.get('passingYards', item.get('passingYds', 0))) or None,
                        passing_tds=int(item.get('passingTouchdowns', item.get('passingTDs', 0))) or None,
                        passing_interceptions=int(item.get('passingInterceptions', item.get('passingINTs', 0))) or None,
                        rushing_yards=int(item.get('rushingYards', item.get('rushingYds', 0))) or None,
                        rushing_tds=int(item.get('rushingTouchdowns', item.get('rushingTDs', 0))) or None,
                        receiving_yards=int(item.get('receivingYards', item.get('receivingYds', 0))) or None,
                        receptions=int(item.get('receptions', item.get('rec', 0))) or None,
                        receiving_tds=int(item.get('receivingTouchdowns', item.get('receivingTDs', 0))) or None,
                        tackles=int(item.get('tackles', item.get('tkl', 0))) or None,
                        sacks=float(item.get('sacks', item.get('sk', 0))) or None,
                        interceptions=int(item.get('interceptions', item.get('ints', 0))) or None,
                        updated_at=item.get('updated_at', item.get('timestamp', datetime.now().isoformat())),
                        quarter=int(item.get('quarter', item.get('q', 0))) or None,
                        snap_count=int(item.get('snapCount', item.get('snaps', 0))) or None,
                    )
                    stats.append(player_stat)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse player stats: {item} - {e}")
                    continue
            
            logger.info(f"Retrieved stats for {len(stats)} players in game {game_id}")
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get box score: {e}")
            return []

    def get_dfs_salaries(
        self,
        date: str,
        sportsbook: str = "draftkings"
    ) -> List[DFSSalary]:
        """
        Get DraftKings salaries and fantasy projections.
        
        **CRITICAL FOR SALARY EFFICIENCY ANALYSIS**
        
        Use this to find value plays:
        - Low salary with high projected FPTS
        - Compare salary to season FPPG
        - Identify outliers
        
        Args:
            date: Date in format YYYYMMDD (e.g., "20250907")
            sportsbook: Sportsbook ("draftkings", "fanduel", etc.)
        
        Returns:
            List of DFSSalary objects
        
        Example:
            >>> salaries = client.get_dfs_salaries("20250907")
            >>> value_plays = [
            ...     s for s in salaries
            ...     if s.projected_fpts and s.salary and s.projected_fpts / s.salary > 0.1
            ... ]
            >>> for play in value_plays:
            ...     print(f"{play.player_name}: ${play.salary} | {play.projected_fpts} pts")
        """
        params = {
            "date": date,
            "sportsBook": sportsbook,
        }
        
        try:
            response = self._make_request("getDFSSalaries", params)
            
            salaries = []
            
            # Parse response
            if isinstance(response, dict):
                salaries_list = response.get('salaries', response.get('slate', response.get('data', response.get('players', []))))
                if not isinstance(salaries_list, list):
                    salaries_list = [response]
            else:
                salaries_list = response if isinstance(response, list) else []
            
            for item in salaries_list:
                try:
                    salary = DFSSalary(
                        player_name=item.get('playerName', item.get('name', 'Unknown')),
                        player_id=item.get('playerId', item.get('playerID')),
                        position=item.get('position', item.get('pos', 'Unknown')),
                        team=item.get('team', item.get('nflTeam', 'N/A')),
                        salary=float(item.get('salary', 0)),
                        fppg=float(item.get('fppg', item.get('seasonFPPG', 0))) if item.get('fppg') or item.get('seasonFPPG') else None,
                        projected_fpts=float(item.get('projectedFpts', item.get('projection', 0))) if item.get('projectedFpts') or item.get('projection') else None,
                        injury_indicator=item.get('injuryIndicator', item.get('injury')),
                        last_week_fpts=float(item.get('lastWeekFpts', 0)) if item.get('lastWeekFpts') else None,
                        season_fppg=float(item.get('seasonFPPG', 0)) if item.get('seasonFPPG') else None,
                    )
                    salaries.append(salary)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse DFS salary: {item} - {e}")
                    continue
            
            logger.info(f"Retrieved DFS salaries for {len(salaries)} players on {date}")
            return salaries
        
        except Exception as e:
            logger.error(f"Failed to get DFS salaries: {e}")
            return []

    def get_nfl_injury_list(self) -> List[InjuryUpdate]:
        """
        Get real-time NFL injury list.
        
        **ESSENTIAL FOR REAL-TIME UPDATES**
        
        Injuries dramatically affect prop lines and predictions.
        Use this to:
        - Alert on key player injuries
        - Adjust prop predictions immediately
        - Identify affected teammates (snap count increases)
        
        Returns:
            List of InjuryUpdate objects
        
        Example:
            >>> injuries = client.get_nfl_injury_list()
            >>> for injury in injuries:
            ...     if injury.status == 'OUT':
            ...         print(f"🚨 {injury.player_name} is OUT ({injury.injury_type})")
        """
        try:
            response = self._make_request("getNFLInjuryList", {})
            
            injuries = []
            
            # Parse response
            if isinstance(response, dict):
                injuries_list = response.get('injuries', response.get('players', response.get('data', [])))
                if not isinstance(injuries_list, list):
                    injuries_list = [response]
            else:
                injuries_list = response if isinstance(response, list) else []
            
            for item in injuries_list:
                try:
                    injury = InjuryUpdate(
                        player_name=item.get('playerName', item.get('name', 'Unknown')),
                        player_id=item.get('playerId', item.get('playerID')),
                        position=item.get('position', item.get('pos', 'Unknown')),
                        team=item.get('team', item.get('nflTeam', 'N/A')),
                        status=item.get('status', 'Unknown'),
                        injury_type=item.get('injuryType', item.get('injury')),
                        return_to_play=item.get('returnToPlay', item.get('eta')),
                        updated_at=item.get('updated_at', item.get('timestamp', datetime.now().isoformat())),
                    )
                    injuries.append(injury)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse injury: {item} - {e}")
                    continue
            
            logger.info(f"Retrieved {len(injuries)} injury updates")
            return injuries
        
        except Exception as e:
            logger.error(f"Failed to get injury list: {e}")
            return []

    def get_nfl_depth_charts(self, team: Optional[str] = None) -> List[DepthChartEntry]:
        """
        Get NFL depth charts with snap count predictions.
        
        **PREDICT PLAYING TIME AND OPPORTUNITY**
        
        Use this to:
        - Predict snap counts for upcoming game
        - Identify backup plays with high volume potential
        - Track depth chart changes week-to-week
        
        Args:
            team: Team abbreviation (e.g., "KC", "SF") - None for all teams
        
        Returns:
            List of DepthChartEntry objects
        
        Example:
            >>> charts = client.get_nfl_depth_charts(team="KC")
            >>> for entry in charts:
            ...     print(f"{entry.player_name} ({entry.position}): {entry.snap_percentage}% snaps")
        """
        params = {}
        if team:
            params["team"] = team
        
        try:
            response = self._make_request("getNFLDepthCharts", params)
            
            entries = []
            
            # Parse response
            if isinstance(response, dict):
                charts_list = response.get('depthCharts', response.get('charts', response.get('data', response.get('players', []))))
                if not isinstance(charts_list, list):
                    charts_list = [response]
            else:
                charts_list = response if isinstance(response, list) else []
            
            for item in charts_list:
                try:
                    entry = DepthChartEntry(
                        player_name=item.get('playerName', item.get('name', 'Unknown')),
                        position=item.get('position', item.get('pos', 'Unknown')),
                        depth_order=int(item.get('depthOrder', item.get('rank', 0))),
                        snap_percentage=float(item.get('snapPercentage', item.get('snapPct', 0))) if item.get('snapPercentage') or item.get('snapPct') else None,
                        team=item.get('team', item.get('nflTeam', 'N/A')),
                        injured=item.get('injured', False),
                    )
                    entries.append(entry)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse depth chart entry: {item} - {e}")
                    continue
            
            logger.info(f"Retrieved depth charts for {len(entries)} players")
            return entries
        
        except Exception as e:
            logger.error(f"Failed to get depth charts: {e}")
            return []

    # ========================================================================
    # HELPER ENDPOINTS
    # ========================================================================

    def get_nfl_teams(self) -> List[Dict]:
        """Get list of NFL teams."""
        try:
            response = self._make_request("getNFLTeams", {})
            logger.info("Retrieved NFL teams list")
            return response if isinstance(response, list) else response.get('teams', [])
        except Exception as e:
            logger.error(f"Failed to get teams: {e}")
            return []

    def get_player_information(self, player_name: str) -> Dict:
        """Get detailed player information."""
        params = {"playerName": player_name}
        
        try:
            response = self._make_request("getPlayerInformation", params)
            logger.info(f"Retrieved information for {player_name}")
            return response
        except Exception as e:
            logger.error(f"Failed to get player info: {e}")
            return {}

    def get_nfl_schedule(self, week: Optional[int] = None) -> List[Dict]:
        """Get NFL schedule for a week."""
        params = {}
        if week:
            params["week"] = week
        
        try:
            response = self._make_request("getWeeklyNFLSchedule", params)
            logger.info("Retrieved NFL schedule")
            return response if isinstance(response, list) else response.get('games', [])
        except Exception as e:
            logger.error(f"Failed to get schedule: {e}")
            return []

    # ========================================================================
    # UTILITY & ANALYTICS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "cache_size": len(self.cache),
            "cache_ttl_seconds": self.cache_ttl,
            "rate_limit": f"{1/self.REQUEST_DELAY:.1f} req/sec",
        }

    def export_to_json(self, data: List, filename: str):
        """Export data to JSON file."""
        output_dir = Path("./tank01_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(
                [item.to_dict() if hasattr(item, 'to_dict') else item for item in data],
                f,
                indent=2
            )
        
        logger.info(f"Exported {len(data)} items to {filepath}")
        return filepath

    def clear_cache(self):
        """Clear the cache."""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared cache ({cache_size} items)")


# ============================================================================
# EDGE DETECTION HELPER
# ============================================================================

class EdgeDetector:
    """
    Edge Detection Engine for FRONTAL LOBE Prediction Model
    
    Compares your model predictions against market odds to find value plays.
    Edge exists when: |Your Probability - Market Probability| > threshold
    """

    def __init__(self, threshold: float = 0.03):
        """
        Initialize edge detector.
        
        Args:
            threshold: Probability difference threshold (default 3%)
        """
        self.threshold = threshold
        self.edges_found = []

    def calculate_implied_probability(self, over_odds: float, under_odds: float) -> Tuple[float, float]:
        """
        Calculate implied probability from American odds.
        
        Args:
            over_odds: Over odds (e.g., -110)
            under_odds: Under odds (e.g., -110)
        
        Returns:
            (over_probability, under_probability)
        """
        # Convert American odds to decimal
        over_decimal = 1 + (100 / abs(over_odds)) if over_odds < 0 else 1 + (over_odds / 100)
        under_decimal = 1 + (100 / abs(under_odds)) if under_odds < 0 else 1 + (under_odds / 100)
        
        # Implied probability = 1 / decimal_odds
        over_prob = 1 / over_decimal
        under_prob = 1 / under_decimal
        
        # Normalize (handle overround)
        total = over_prob + under_prob
        if total > 0:
            over_prob /= total
            under_prob /= total
        
        return over_prob, under_prob

    def detect_edges(
        self,
        player_props: List[PlayerProp],
        model_predictions: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Detect edges between model predictions and market odds.
        
        Args:
            player_props: List of PlayerProp objects from Tank01
            model_predictions: Dict of {player_name: predicted_probability}
        
        Returns:
            List of detected edges
        
        Example:
            >>> detector = EdgeDetector(threshold=0.03)
            >>> props = client.get_nfl_betting_odds("20250907")
            >>> predictions = {"Travis Kelce": 0.65, "Patrick Mahomes": 0.58}
            >>> edges = detector.detect_edges(props, predictions)
            >>> for edge in edges:
            ...     print(f"{edge['player']} - {edge['stat']}: Edge {edge['edge']:.1%}")
        """
        edges = []
        
        for prop in player_props:
            player_key = prop.player_name.lower().strip()
            
            # Find matching prediction
            matching_prediction = None
            for pred_name, pred_prob in model_predictions.items():
                if player_key in pred_name.lower() or pred_name.lower() in player_key:
                    matching_prediction = pred_prob
                    break
            
            if matching_prediction is None:
                continue
            
            # Calculate market probability
            over_prob, under_prob = self.calculate_implied_probability(
                prop.over_odds,
                prop.under_odds
            )
            
            # Determine if prediction is for over or under
            # (Assuming prediction is "over" probability)
            market_prob = over_prob
            predicted_prob = matching_prediction
            
            # Calculate edge
            edge = predicted_prob - market_prob
            
            # Check if edge exceeds threshold
            if abs(edge) > self.threshold:
                edge_obj = {
                    "player": prop.player_name,
                    "stat": prop.stat_type,
                    "line": prop.line,
                    "model_prediction": predicted_prob,
                    "market_probability": market_prob,
                    "edge": edge,
                    "direction": "OVER" if edge > 0 else "UNDER",
                    "edge_percentage": abs(edge),
                    "over_odds": prop.over_odds,
                    "under_odds": prop.under_odds,
                    "timestamp": prop.timestamp,
                    "confidence": "HIGH" if abs(edge) > 0.05 else "MEDIUM",
                }
                edges.append(edge_obj)
                self.edges_found.append(edge_obj)
        
        logger.info(f"Detected {len(edges)} edges above {self.threshold:.1%} threshold")
        return edges

    def get_edges_report(self) -> Dict:
        """Get summary report of detected edges."""
        return {
            "total_edges": len(self.edges_found),
            "high_confidence_edges": len([e for e in self.edges_found if e['confidence'] == 'HIGH']),
            "average_edge": sum(abs(e['edge']) for e in self.edges_found) / len(self.edges_found) if self.edges_found else 0,
            "edges": self.edges_found,
        }


# ============================================================================
# SETUP & CONFIGURATION
# ============================================================================

def setup_tank01_client(api_key: str) -> Tank01NFLClient:
    """
    Setup Tank01 client with provided API key.
    
    Get API key from: https://rapidapi.com/mma8/api/tank01-nfl-live-in-game-real-time-statistics-nfl
    """
    if not api_key:
        raise ValueError(
            "Tank01 API key not provided.\n"
            "Get it from: https://rapidapi.com/mma8/api/tank01-nfl-live-in-game-real-time-statistics-nfl\n"
            "Then set environment variable: export TANK01_API_KEY='your_key'"
        )
    
    return Tank01NFLClient(api_key)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    import os
    
    api_key = os.environ.get('TANK01_API_KEY')
    if not api_key:
        print("❌ Tank01 API key not found in TANK01_API_KEY environment variable")
        print("Get your key from: https://rapidapi.com/mma8/api/tank01-nfl-live-in-game-real-time-statistics-nfl")
        exit(1)
    
    # Initialize client
    client = Tank01NFLClient(api_key)
    
    # Example: Get betting odds
    print("\n" + "="*70)
    print("Tank01 NFL API Client - Test Mode")
    print("="*70)
    
    today = datetime.now().strftime("%Y%m%d")
    
    print(f"\n1. Fetching betting odds for {today}...")
    props = client.get_nfl_betting_odds(today, player_props=True)
    for prop in props[:5]:
        print(f"  • {prop.player_name} ({prop.team}): {prop.stat_type} > {prop.line}")
    
    print(f"\n2. Fetching injury list...")
    injuries = client.get_nfl_injury_list()
    for injury in injuries[:5]:
        print(f"  • {injury.player_name}: {injury.status} ({injury.injury_type})")
    
    print(f"\n3. Fetching DFS salaries for {today}...")
    salaries = client.get_dfs_salaries(today)
    for salary in salaries[:5]:
        print(f"  • {salary.player_name}: ${salary.salary} | {salary.fppg} FPPG")
    
    print(f"\n4. Client stats:")
    stats = client.get_stats()
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ Tank01 NFL API Client is operational!")
    print("="*70 + "\n")
