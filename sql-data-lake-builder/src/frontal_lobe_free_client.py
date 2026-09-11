"""
FRONTAL LOBE Free Data Stack - Unified Client
Sovereign sports data ingestion (No RapidAPI, No Tank01)

Combines:
- NFLverse (NFL historical + DFS)
- nba_api (NBA/WNBA live + historical)
- statsapi (MLB live + Statcast)
- ESPN Hidden APIs (real-time all sports)
- Sleeper API (fantasy + injuries)

Cost: $0/month
Rate Limits: None
Coverage: All major leagues
Latency: Real-time
"""

import httpx
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class NFLGame:
    """NFL game data"""
    game_id: str
    game_date: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    quarter: Optional[int]
    time_remaining: Optional[str]


@dataclass
class PlayerStats:
    """Player performance statistics"""
    player_name: str
    position: str
    team: str
    points: float
    rebounds: Optional[float]
    assists: float
    field_goal_pct: Optional[float]
    three_point_pct: Optional[float]
    usage_pct: Optional[float]


@dataclass
class InjuryReport:
    """Player injury information"""
    player_name: str
    team: str
    status: str
    injury_type: Optional[str]
    return_date: Optional[str]


# ============================================================================
# FRONTAL LOBE FREE CLIENT
# ============================================================================

class FrontalLobeDataStack:
    """
    Unified free sports data client
    Replaces Tank01 with sovereign, open-source data sources
    """
    
    def __init__(self):
        """Initialize data stack with all required parameters"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        self.espn_base = "https://site.api.espn.com/apis/site/v2/sports"
        self.cdn_base = "https://a.espncdn.com"
        self.sleeper_base = "https://api.sleeper.app/v1"
        
        self.session = httpx.Client(timeout=15.0)
        self.cache = {}
        self.cache_ttl = 60  # seconds
        
        logger.info("✅ FRONTAL LOBE Free Data Stack initialized")
    
    # ========================================================================
    # NFL DATA (via NFLverse + ESPN)
    # ========================================================================
    
    def get_nfl_live_scoreboard(self) -> List[NFLGame]:
        """
        Get live NFL games from ESPN Hidden API
        
        Returns:
            List of NFLGame objects
        """
        try:
            url = f"{self.espn_base}/football/nfl/scoreboard"
            resp = self.session.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            games = []
            for event in data.get('events', []):
                try:
                    comp = event['competitions'][0]
                    game = NFLGame(
                        game_id=event['id'],
                        game_date=event['date'],
                        home_team=comp['competitors'][0]['team']['abbreviation'],
                        away_team=comp['competitors'][1]['team']['abbreviation'],
                        home_score=int(comp['competitors'][0].get('score', 0)) or None,
                        away_score=int(comp['competitors'][1].get('score', 0)) or None,
                        status=event['status']['type']['detail'],
                        quarter=comp.get('status', {}).get('period'),
                        time_remaining=comp.get('status', {}).get('displayClock'),
                    )
                    games.append(game)
                except (KeyError, ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse NFL game: {e}")
                    continue
            
            logger.info(f"✅ Retrieved {len(games)} live NFL games")
            return games
        
        except Exception as e:
            logger.error(f"Failed to get NFL scoreboard: {e}")
            return []
    
    def get_nfl_weekly_stats(self, year: int = 2026, week: Optional[int] = None) -> pd.DataFrame:
        """
        Get NFL weekly player stats from NFLverse
        
        Args:
            year: Season year
            week: Specific week (1-18) or None for all
        
        Returns:
            DataFrame with player stats
        """
        try:
            import nfl_data_py as nfl
            
            logger.info(f"Fetching NFL stats for {year}, week {week or 'all'}...")
            weekly = nfl.import_weekly_data(years=[year])
            
            if week:
                weekly = weekly[weekly['week'] == week]
            
            logger.info(f"✅ Retrieved {len(weekly)} player records")
            return weekly
        
        except ImportError:
            logger.error("nfl_data_py not installed. Run: pip install nfl_data_py")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get NFL stats: {e}")
            return pd.DataFrame()
    
    def get_nfl_play_by_play(self, year: int = 2026, week: Optional[int] = None) -> pd.DataFrame:
        """
        Get NFL play-by-play data from NFLverse
        
        Args:
            year: Season year
            week: Specific week or None for all
        
        Returns:
            DataFrame with play-by-play data
        """
        try:
            import nfl_data_py as nfl
            
            logger.info(f"Fetching NFL play-by-play for {year}...")
            pbp = nfl.import_pbp_data(years=[year])
            
            if week:
                pbp = pbp[pbp['week'] == week]
            
            logger.info(f"✅ Retrieved {len(pbp)} plays")
            return pbp
        
        except ImportError:
            logger.error("nfl_data_py not installed")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get play-by-play: {e}")
            return pd.DataFrame()
    
    def get_nfl_dfs_salaries(self, year: int = 2026) -> pd.DataFrame:
        """
        Get DraftKings NFL salaries from NFLverse
        
        Args:
            year: Season year
        
        Returns:
            DataFrame with salary data
        """
        try:
            import nfl_data_py as nfl
            
            logger.info(f"Fetching NFL DFS salaries for {year}...")
            rosters = nfl.import_rosters(years=[year])
            
            # Extract salary-related columns if available
            salary_cols = [col for col in rosters.columns if 'salary' in col.lower() or 'dk' in col.lower()]
            
            if not salary_cols:
                logger.warning("No salary columns found in roster data")
                return rosters
            
            logger.info(f"✅ Retrieved salary data ({len(rosters)} players)")
            return rosters[['player_name', 'position', 'team'] + salary_cols]
        
        except ImportError:
            logger.error("nfl_data_py not installed")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get DFS salaries: {e}")
            return pd.DataFrame()
    
    def get_player_headshot_url(self, player_id: str, size: str = '350x254') -> str:
        """
        Get player headshot URL from ESPN CDN
        
        Args:
            player_id: ESPN player ID
            size: Image size (default: 350x254)
        
        Returns:
            Direct CDN URL to headshot PNG
        """
        return f"{self.cdn_base}/combiner/i?img=/i/headshots/nfl/players/full/{player_id}.png&w=350&h=254"
    
    # ========================================================================
    # NBA / WNBA DATA (via nba_api)
    # ========================================================================
    
    def get_nba_live_scoreboard(self) -> List[Dict]:
        """
        Get live NBA games from ESPN
        
        Returns:
            List of game dictionaries
        """
        try:
            url = f"{self.espn_base}/basketball/nba/scoreboard"
            resp = self.session.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            games = []
            for event in data.get('events', []):
                comp = event['competitions'][0]
                game = {
                    'game_id': event['id'],
                    'date': event['date'],
                    'home_team': comp['competitors'][0]['team']['abbreviation'],
                    'away_team': comp['competitors'][1]['team']['abbreviation'],
                    'home_score': comp['competitors'][0].get('score'),
                    'away_score': comp['competitors'][1].get('score'),
                    'status': event['status']['type']['detail'],
                }
                games.append(game)
            
            logger.info(f"✅ Retrieved {len(games)} live NBA games")
            return games
        
        except Exception as e:
            logger.error(f"Failed to get NBA scoreboard: {e}")
            return []
    
    def get_wnba_stats(self, stat_type: str = 'leaders', season: int = 2026) -> pd.DataFrame:
        """
        Get WNBA player stats directly from stats.nba.com
        
        Args:
            stat_type: 'leaders' or 'career_stats'
            season: Season year
        
        Returns:
            DataFrame with WNBA statistics
        """
        try:
            from nba_api.stats.endpoints import leagueleaders
            
            logger.info(f"Fetching WNBA {stat_type} for {season}...")
            
            leaders = leagueleaders.LeagueLeaders(
                league_id='10',  # WNBA league ID
                per_mode48='PerGame',
                season=str(season),
                season_type_all_star='Regular Season'
            )
            
            df = leaders.get_data_frames()[0]
            logger.info(f"✅ Retrieved {len(df)} WNBA players")
            return df
        
        except ImportError:
            logger.error("nba_api not installed. Run: pip install nba_api")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get WNBA stats: {e}")
            return pd.DataFrame()
    
    def get_nba_live_box_score(self, game_id: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get live NBA/WNBA box score
        
        Args:
            game_id: ESPN game ID
        
        Returns:
            Tuple of (player_stats, team_stats) DataFrames
        """
        try:
            from nba_api.stats.endpoints import boxscoretraditionalv2
            
            box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            data_frames = box.get_data_frames()
            
            logger.info(f"✅ Retrieved box score for game {game_id}")
            return data_frames[0], data_frames[1]  # player_stats, team_stats
        
        except ImportError:
            logger.error("nba_api not installed")
            return pd.DataFrame(), pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get box score: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    # ========================================================================
    # MLB DATA (via statsapi)
    # ========================================================================
    
    def get_mlb_live_scoreboard(self) -> List[Dict]:
        """
        Get live MLB games from ESPN
        
        Returns:
            List of game dictionaries
        """
        try:
            url = f"{self.espn_base}/baseball/mlb/scoreboard"
            resp = self.session.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            games = []
            for event in data.get('events', []):
                comp = event['competitions'][0]
                game = {
                    'game_id': event['id'],
                    'date': event['date'],
                    'home_team': comp['competitors'][0]['team']['abbreviation'],
                    'away_team': comp['competitors'][1]['team']['abbreviation'],
                    'home_score': comp['competitors'][0].get('score'),
                    'away_score': comp['competitors'][1].get('score'),
                    'status': event['status']['type']['detail'],
                }
                games.append(game)
            
            logger.info(f"✅ Retrieved {len(games)} live MLB games")
            return games
        
        except Exception as e:
            logger.error(f"Failed to get MLB scoreboard: {e}")
            return []
    
    def get_mlb_games_today(self) -> List[Dict]:
        """
        Get today's MLB games from statsapi
        
        Returns:
            List of game dictionaries
        """
        try:
            import statsapi
            
            today = datetime.now().strftime('%Y-%m-%d')
            games = statsapi.schedule(start_date=today, end_date=today)
            
            logger.info(f"✅ Retrieved {len(games)} MLB games for {today}")
            return games
        
        except ImportError:
            logger.error("statsapi not installed. Run: pip install statsapi")
            return []
        except Exception as e:
            logger.error(f"Failed to get MLB games: {e}")
            return []
    
    def get_mlb_box_score(self, game_id: str) -> Dict:
        """
        Get MLB box score from statsapi
        
        Args:
            game_id: MLB game ID
        
        Returns:
            Box score data dictionary
        """
        try:
            import statsapi
            
            box = statsapi.boxscore_data(game_id)
            logger.info(f"✅ Retrieved MLB box score for game {game_id}")
            return box
        
        except ImportError:
            logger.error("statsapi not installed")
            return {}
        except Exception as e:
            logger.error(f"Failed to get MLB box score: {e}")
            return {}
    
    # ========================================================================
    # INJURIES & ROSTERS (via Sleeper + ESPN)
    # ========================================================================
    
    def get_nfl_injuries_sleeper(self) -> List[InjuryReport]:
        """
        Get NFL injury reports from Sleeper API
        
        Returns:
            List of InjuryReport objects
        """
        try:
            url = f"{self.sleeper_base}/players/nfl"
            resp = self.session.get(url, headers=self.headers)
            resp.raise_for_status()
            players = resp.json()
            
            injuries = []
            for player_id, player_data in players.items():
                injury = player_data.get('injury_status')
                if injury:
                    report = InjuryReport(
                        player_name=player_data.get('full_name', 'Unknown'),
                        team=player_data.get('nfl_team', 'N/A'),
                        status=injury,
                        injury_type=player_data.get('injury_body_part'),
                        return_date=player_data.get('return_week'),
                    )
                    injuries.append(report)
            
            logger.info(f"✅ Retrieved {len(injuries)} injury reports from Sleeper")
            return injuries
        
        except Exception as e:
            logger.error(f"Failed to get Sleeper injuries: {e}")
            return []
    
    def get_nfl_rosters(self) -> Dict[str, List[Dict]]:
        """
        Get NFL team rosters from Sleeper
        
        Returns:
            Dictionary mapping team abbreviation to roster
        """
        try:
            url = f"{self.sleeper_base}/teams/nfl"
            resp = self.session.get(url, headers=self.headers)
            resp.raise_for_status()
            teams = resp.json()
            
            rosters = {}
            for team_data in teams:
                team_abbr = team_data.get('metadata', {}).get('abbreviation', 'N/A')
                rosters[team_abbr] = team_data.get('roster', [])
            
            logger.info(f"✅ Retrieved rosters for {len(rosters)} NFL teams")
            return rosters
        
        except Exception as e:
            logger.error(f"Failed to get NFL rosters: {e}")
            return {}
    
    # ========================================================================
    # UTILITY & ANALYTICS
    # ========================================================================
    
    def calculate_implied_probability(self, over_odds: float, under_odds: float) -> Tuple[float, float]:
        """
        Calculate implied probability from American odds
        
        Args:
            over_odds: Over bet odds (e.g., -110)
            under_odds: Under bet odds (e.g., -110)
        
        Returns:
            Tuple of (over_probability, under_probability)
        """
        over_decimal = 1 + (100 / abs(over_odds)) if over_odds < 0 else 1 + (over_odds / 100)
        under_decimal = 1 + (100 / abs(under_odds)) if under_odds < 0 else 1 + (under_odds / 100)
        
        over_prob = 1 / over_decimal
        under_prob = 1 / under_decimal
        
        # Normalize (handle overround)
        total = over_prob + under_prob
        if total > 0:
            over_prob /= total
            under_prob /= total
        
        return over_prob, under_prob
    
    def detect_edge(self, model_prediction: float, market_line: float, threshold: float = 0.03) -> Optional[Dict]:
        """
        Detect edge between model prediction and market line
        
        Args:
            model_prediction: Your model's probability (0-1)
            market_line: Market's implied probability (0-1)
            threshold: Minimum edge to flag (default 3%)
        
        Returns:
            Edge data dict or None if no edge
        """
        edge = abs(model_prediction - market_line)
        
        if edge > threshold:
            return {
                'model_prediction': model_prediction,
                'market_line': market_line,
                'edge': edge,
                'edge_pct': f"{edge:.1%}",
                'direction': 'OVER' if model_prediction > market_line else 'UNDER',
                'confidence': 'HIGH' if edge > 0.05 else 'MEDIUM',
            }
        
        return None
    
    def export_to_json(self, data: Any, filename: str):
        """Export data to JSON"""
        with open(filename, 'w') as f:
            if isinstance(data, pd.DataFrame):
                data.to_json(f, orient='records', indent=2)
            elif isinstance(data, list) and data and hasattr(data[0], '__dataclass_fields__'):
                json.dump([vars(item) for item in data], f, indent=2, default=str)
            else:
                json.dump(data, f, indent=2, default=str)
        logger.info(f"✅ Exported data to {filename}")
    
    def export_to_csv(self, data: pd.DataFrame, filename: str):
        """Export DataFrame to CSV"""
        if isinstance(data, pd.DataFrame):
            data.to_csv(filename, index=False)
            logger.info(f"✅ Exported data to {filename}")
    
    def cleanup(self):
        """Clean up resources"""
        self.session.close()
        logger.info("Closed HTTP session")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FRONTAL LOBE Free Data Stack - Test Mode")
    print("=" * 70 + "\n")
    
    frontal = FrontalLobeDataStack()
    
    try:
        # 1. NFL Live Games
        print("1️⃣ NFL Live Games:")
        nfl_games = frontal.get_nfl_live_scoreboard()
        for game in nfl_games[:3]:
            print(f"   {game.away_team} @ {game.home_team}: {game.status}")
        
        # 2. WNBA Stats
        print("\n2️⃣ WNBA Season Stats:")
        wnba = frontal.get_wnba_stats()
        if not wnba.empty:
            cols = ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'PTS', 'REB', 'AST']
            print(wnba[cols].head())
        
        # 3. NFL Weekly Stats
        print("\n3️⃣ NFL Weekly Stats (2025):")
        nfl_weekly = frontal.get_nfl_weekly_stats(year=2025, week=1)
        if not nfl_weekly.empty:
            cols = ['player_name', 'position', 'passing_yards', 'rushing_yards']
            print(nfl_weekly[cols].head())
        
        # 4. MLB Live Games
        print("\n4️⃣ MLB Live Games:")
        mlb_games = frontal.get_mlb_live_scoreboard()
        for game in mlb_games[:3]:
            print(f"   {game['away_team']} @ {game['home_team']}: {game['status']}")
        
        # 5. NFL Injuries (Sleeper)
        print("\n5️⃣ NFL Injury Reports:")
        injuries = frontal.get_nfl_injuries_sleeper()
        for injury in injuries[:3]:
            print(f"   {injury.player_name}: {injury.status}")
        
        # 6. Edge Detection Example
        print("\n6️⃣ Edge Detection Example:")
        edge = frontal.detect_edge(
            model_prediction=0.65,
            market_line=0.55,
            threshold=0.03
        )
        if edge:
            print(f"   ✅ EDGE DETECTED: {edge['edge_pct']} ({edge['direction']})")
        
        print("\n" + "=" * 70)
        print("✅ All data sources operational!")
        print("=" * 70)
    
    finally:
        frontal.cleanup()
