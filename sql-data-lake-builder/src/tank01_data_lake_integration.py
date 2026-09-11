"""
Tank01 → PostgreSQL Data Lake Integration

This module connects real-time Tank01 NFL API data to your PostgreSQL database.

Architecture:
  1. Tank01 API Client fetches real-time data (every 5-60 seconds)
  2. Data is normalized and validated
  3. Stored in PostgreSQL tables (with TimescaleDB hypertables for time-series)
  4. Historical + Real-time data combined for FRONTAL LOBE model input
  5. Edge detection runs continuously

Tables Created:
  - tank01_player_props: Real-time betting odds (time-series)
  - tank01_game_stats: Live game statistics (time-series)
  - tank01_dfs_salaries: DraftKings salary slate (time-series)
  - tank01_injuries: Real-time injury updates (time-series)
  - tank01_depth_charts: Depth chart snapshots (time-series)
  - tank01_edge_alerts: Detected edges (for FRONTAL LOBE execution)

Author: FRONTAL LOBE Data Lake Team
Version: 1.0.0
"""

import psycopg2
from psycopg2 import sql, extras, Error
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from tank01_api_client import (
    Tank01NFLClient,
    PlayerProp,
    PlayerGameStats,
    InjuryUpdate,
    DFSSalary,
    DepthChartEntry,
    EdgeDetector,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE CONNECTION & SCHEMA SETUP
# ============================================================================

class Tank01DataLakeConnection:
    """PostgreSQL connection manager for Tank01 data lake."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "sports_data_lake",
        user: str = "sports_user",
        password: str = "sports_password",
        use_timescaledb: bool = True
    ):
        """
        Initialize database connection.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            use_timescaledb: Enable TimescaleDB for time-series tables
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.use_timescaledb = use_timescaledb
        self.conn = None

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=5
            )
            logger.info(f"✅ Connected to PostgreSQL: {self.user}@{self.host}:{self.port}/{self.database}")
            return True
        except Error as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from PostgreSQL")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute query and return result."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except Error as e:
            logger.error(f"Query execution failed: {e}")
            self.conn.rollback()
            return None

    def create_tables(self) -> bool:
        """Create Tank01 data lake tables."""
        try:
            cursor = self.conn.cursor()
            
            # ================================================================
            # PLAYER PROPS TABLE (Time-Series: Betting Odds)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_player_props (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    game_id VARCHAR(50),
                    game_date DATE,
                    player_id VARCHAR(50),
                    player_name VARCHAR(255) NOT NULL,
                    position VARCHAR(10),
                    team VARCHAR(10),
                    stat_type VARCHAR(100),
                    line FLOAT,
                    over_odds FLOAT,
                    under_odds FLOAT,
                    implied_total FLOAT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # Create index for time-series queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_props_timestamp 
                ON tank01_player_props (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_props_player 
                ON tank01_player_props (player_name, stat_type, timestamp DESC);
            """)
            
            # Convert to TimescaleDB hypertable if enabled
            if self.use_timescaledb:
                try:
                    cursor.execute("""
                        SELECT create_hypertable('tank01_player_props', 'timestamp', 
                        if_not_exists => TRUE);
                    """)
                    logger.info("✅ Created TimescaleDB hypertable: tank01_player_props")
                except:
                    logger.info("⚠️  TimescaleDB hypertable already exists or not available")
            
            # ================================================================
            # GAME STATS TABLE (Time-Series: Live Stats)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_game_stats (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    game_id VARCHAR(50) NOT NULL,
                    player_id VARCHAR(50),
                    player_name VARCHAR(255) NOT NULL,
                    position VARCHAR(10),
                    team VARCHAR(10),
                    passing_yards INT,
                    passing_tds INT,
                    passing_interceptions INT,
                    rushing_yards INT,
                    rushing_tds INT,
                    receiving_yards INT,
                    receptions INT,
                    receiving_tds INT,
                    tackles INT,
                    sacks FLOAT,
                    interceptions INT,
                    quarter INT,
                    snap_count INT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_stats_timestamp 
                ON tank01_game_stats (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_stats_game 
                ON tank01_game_stats (game_id, player_name, timestamp DESC);
            """)
            
            if self.use_timescaledb:
                try:
                    cursor.execute("""
                        SELECT create_hypertable('tank01_game_stats', 'timestamp', 
                        if_not_exists => TRUE);
                    """)
                    logger.info("✅ Created TimescaleDB hypertable: tank01_game_stats")
                except:
                    pass
            
            # ================================================================
            # DFS SALARIES TABLE (Time-Series: Salary Slate)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_dfs_salaries (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    date_slate DATE,
                    player_id VARCHAR(50),
                    player_name VARCHAR(255) NOT NULL,
                    position VARCHAR(10),
                    team VARCHAR(10),
                    salary FLOAT,
                    fppg FLOAT,
                    projected_fpts FLOAT,
                    injury_indicator VARCHAR(50),
                    last_week_fpts FLOAT,
                    season_fppg FLOAT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_salaries_timestamp 
                ON tank01_dfs_salaries (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_salaries_date 
                ON tank01_dfs_salaries (date_slate, player_name);
            """)
            
            if self.use_timescaledb:
                try:
                    cursor.execute("""
                        SELECT create_hypertable('tank01_dfs_salaries', 'timestamp', 
                        if_not_exists => TRUE);
                    """)
                    logger.info("✅ Created TimescaleDB hypertable: tank01_dfs_salaries")
                except:
                    pass
            
            # ================================================================
            # INJURIES TABLE (Time-Series: Real-Time Status Updates)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_injuries (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    player_id VARCHAR(50),
                    player_name VARCHAR(255) NOT NULL,
                    position VARCHAR(10),
                    team VARCHAR(10),
                    status VARCHAR(50),
                    injury_type VARCHAR(100),
                    return_to_play VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_injuries_timestamp 
                ON tank01_injuries (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_injuries_player 
                ON tank01_injuries (player_name, timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_injuries_status 
                ON tank01_injuries (status, timestamp DESC);
            """)
            
            if self.use_timescaledb:
                try:
                    cursor.execute("""
                        SELECT create_hypertable('tank01_injuries', 'timestamp', 
                        if_not_exists => TRUE);
                    """)
                    logger.info("✅ Created TimescaleDB hypertable: tank01_injuries")
                except:
                    pass
            
            # ================================================================
            # DEPTH CHARTS TABLE (Time-Series: Snap Predictions)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_depth_charts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    player_name VARCHAR(255) NOT NULL,
                    position VARCHAR(10),
                    depth_order INT,
                    snap_percentage FLOAT,
                    team VARCHAR(10),
                    injured BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_depth_timestamp 
                ON tank01_depth_charts (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_depth_team 
                ON tank01_depth_charts (team, position, timestamp DESC);
            """)
            
            if self.use_timescaledb:
                try:
                    cursor.execute("""
                        SELECT create_hypertable('tank01_depth_charts', 'timestamp', 
                        if_not_exists => TRUE);
                    """)
                    logger.info("✅ Created TimescaleDB hypertable: tank01_depth_charts")
                except:
                    pass
            
            # ================================================================
            # EDGE ALERTS TABLE (Edge Detection Results)
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank01_edge_alerts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    player_name VARCHAR(255) NOT NULL,
                    stat_type VARCHAR(100),
                    line FLOAT,
                    model_prediction FLOAT,
                    market_probability FLOAT,
                    edge FLOAT,
                    direction VARCHAR(10),
                    edge_percentage FLOAT,
                    over_odds FLOAT,
                    under_odds FLOAT,
                    confidence VARCHAR(20),
                    status VARCHAR(50) DEFAULT 'ACTIVE',
                    executed_at TIMESTAMPTZ,
                    profit_loss FLOAT,
                    notes TEXT
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_edges_timestamp 
                ON tank01_edge_alerts (timestamp DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tank01_edges_status 
                ON tank01_edge_alerts (status, timestamp DESC);
            """)
            
            self.conn.commit()
            logger.info("✅ Tank01 data lake tables created successfully")
            return True
        
        except Error as e:
            logger.error(f"❌ Table creation failed: {e}")
            self.conn.rollback()
            return False

    def upsert_player_prop(self, prop: PlayerProp) -> bool:
        """Upsert player prop into database."""
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_player_props (
                    timestamp, game_id, game_date, player_id, player_name, position, team,
                    stat_type, line, over_odds, under_odds, implied_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                datetime.now(),
                prop.game_id,
                datetime.strptime(prop.game_date, "%Y%m%d").date() if prop.game_date else None,
                prop.player_id,
                prop.player_name,
                prop.position,
                prop.team,
                prop.stat_type,
                prop.line,
                prop.over_odds,
                prop.under_odds,
                prop.implied_total,
            ))
            
            self.conn.commit()
            return True
        
        except Error as e:
            logger.error(f"Failed to insert player prop: {e}")
            self.conn.rollback()
            return False

    def batch_upsert_player_props(self, props: List[PlayerProp]) -> int:
        """Batch upsert player props into database."""
        if not props:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_player_props (
                    timestamp, game_id, game_date, player_id, player_name, position, team,
                    stat_type, line, over_odds, under_odds, implied_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for prop in props:
                rows.append((
                    datetime.now(),
                    prop.game_id,
                    datetime.strptime(prop.game_date, "%Y%m%d").date() if prop.game_date else None,
                    prop.player_id,
                    prop.player_name,
                    prop.position,
                    prop.team,
                    prop.stat_type,
                    prop.line,
                    prop.over_odds,
                    prop.under_odds,
                    prop.implied_total,
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(props)} player props")
            return len(props)
        
        except Error as e:
            logger.error(f"Failed to batch insert player props: {e}")
            self.conn.rollback()
            return 0

    def batch_upsert_game_stats(self, stats: List[PlayerGameStats]) -> int:
        """Batch upsert game stats into database."""
        if not stats:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_game_stats (
                    timestamp, game_id, player_id, player_name, position, team,
                    passing_yards, passing_tds, passing_interceptions,
                    rushing_yards, rushing_tds,
                    receiving_yards, receptions, receiving_tds,
                    tackles, sacks, interceptions,
                    quarter, snap_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for stat in stats:
                rows.append((
                    datetime.now(),
                    stat.game_id,
                    stat.player_id,
                    stat.player_name,
                    stat.position,
                    stat.team,
                    stat.passing_yards,
                    stat.passing_tds,
                    stat.passing_interceptions,
                    stat.rushing_yards,
                    stat.rushing_tds,
                    stat.receiving_yards,
                    stat.receptions,
                    stat.receiving_tds,
                    stat.tackles,
                    stat.sacks,
                    stat.interceptions,
                    stat.quarter,
                    stat.snap_count,
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(stats)} game statistics")
            return len(stats)
        
        except Error as e:
            logger.error(f"Failed to batch insert game stats: {e}")
            self.conn.rollback()
            return 0

    def batch_upsert_dfs_salaries(self, salaries: List[DFSSalary]) -> int:
        """Batch upsert DFS salaries into database."""
        if not salaries:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_dfs_salaries (
                    timestamp, date_slate, player_id, player_name, position, team,
                    salary, fppg, projected_fpts, injury_indicator, last_week_fpts, season_fppg
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for salary in salaries:
                rows.append((
                    datetime.now(),
                    datetime.now().date(),
                    salary.player_id,
                    salary.player_name,
                    salary.position,
                    salary.team,
                    salary.salary,
                    salary.fppg,
                    salary.projected_fpts,
                    salary.injury_indicator,
                    salary.last_week_fpts,
                    salary.season_fppg,
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(salaries)} DFS salaries")
            return len(salaries)
        
        except Error as e:
            logger.error(f"Failed to batch insert DFS salaries: {e}")
            self.conn.rollback()
            return 0

    def batch_upsert_injuries(self, injuries: List[InjuryUpdate]) -> int:
        """Batch upsert injury updates into database."""
        if not injuries:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_injuries (
                    timestamp, player_id, player_name, position, team,
                    status, injury_type, return_to_play
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for injury in injuries:
                rows.append((
                    datetime.now(),
                    injury.player_id,
                    injury.player_name,
                    injury.position,
                    injury.team,
                    injury.status,
                    injury.injury_type,
                    injury.return_to_play,
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(injuries)} injury updates")
            return len(injuries)
        
        except Error as e:
            logger.error(f"Failed to batch insert injuries: {e}")
            self.conn.rollback()
            return 0

    def batch_upsert_depth_charts(self, entries: List[DepthChartEntry]) -> int:
        """Batch upsert depth chart entries into database."""
        if not entries:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_depth_charts (
                    timestamp, player_name, position, depth_order, snap_percentage, team, injured
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for entry in entries:
                rows.append((
                    datetime.now(),
                    entry.player_name,
                    entry.position,
                    entry.depth_order,
                    entry.snap_percentage,
                    entry.team,
                    entry.injured,
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(entries)} depth chart entries")
            return len(entries)
        
        except Error as e:
            logger.error(f"Failed to batch insert depth charts: {e}")
            self.conn.rollback()
            return 0

    def insert_edge_alert(self, edge: Dict) -> bool:
        """Insert edge detection alert into database."""
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_edge_alerts (
                    timestamp, player_name, stat_type, line, model_prediction,
                    market_probability, edge, direction, edge_percentage, over_odds,
                    under_odds, confidence, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                datetime.now(),
                edge.get('player'),
                edge.get('stat'),
                edge.get('line'),
                edge.get('model_prediction'),
                edge.get('market_probability'),
                edge.get('edge'),
                edge.get('direction'),
                edge.get('edge_percentage'),
                edge.get('over_odds'),
                edge.get('under_odds'),
                edge.get('confidence'),
                'ACTIVE',
                f"Edge: {edge.get('edge_percentage', 0):.1%}",
            ))
            
            self.conn.commit()
            return True
        
        except Error as e:
            logger.error(f"Failed to insert edge alert: {e}")
            self.conn.rollback()
            return False

    def batch_insert_edge_alerts(self, edges: List[Dict]) -> int:
        """Batch insert edge detection alerts into database."""
        if not edges:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            query = """
                INSERT INTO tank01_edge_alerts (
                    timestamp, player_name, stat_type, line, model_prediction,
                    market_probability, edge, direction, edge_percentage, over_odds,
                    under_odds, confidence, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for edge in edges:
                rows.append((
                    datetime.now(),
                    edge.get('player'),
                    edge.get('stat'),
                    edge.get('line'),
                    edge.get('model_prediction'),
                    edge.get('market_probability'),
                    edge.get('edge'),
                    edge.get('direction'),
                    edge.get('edge_percentage'),
                    edge.get('over_odds'),
                    edge.get('under_odds'),
                    edge.get('confidence'),
                    'ACTIVE',
                    f"Edge: {edge.get('edge_percentage', 0):.1%}",
                ))
            
            extras.execute_batch(cursor, query, rows, page_size=1000)
            self.conn.commit()
            
            logger.info(f"✅ Inserted {len(edges)} edge alerts")
            return len(edges)
        
        except Error as e:
            logger.error(f"Failed to batch insert edge alerts: {e}")
            self.conn.rollback()
            return 0

    def get_recent_props(self, player_name: str, stat_type: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Get recent player props for analysis."""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.DictCursor)
            
            query = """
                SELECT * FROM tank01_player_props
                WHERE player_name = %s
                AND timestamp > NOW() - INTERVAL '%s hours'
            """
            
            params = [player_name, hours]
            
            if stat_type:
                query += " AND stat_type = %s"
                params.append(stat_type)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
        
        except Error as e:
            logger.error(f"Failed to get recent props: {e}")
            return []

    def get_latest_edge_alerts(self, limit: int = 20) -> List[Dict]:
        """Get latest edge detection alerts."""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.DictCursor)
            
            query = """
                SELECT * FROM tank01_edge_alerts
                WHERE status = 'ACTIVE'
                ORDER BY timestamp DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            return cursor.fetchall()
        
        except Error as e:
            logger.error(f"Failed to get edge alerts: {e}")
            return []

    def get_player_game_stats(self, player_name: str, game_id: str) -> List[Dict]:
        """Get player stats for a specific game."""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.DictCursor)
            
            query = """
                SELECT * FROM tank01_game_stats
                WHERE player_name = %s AND game_id = %s
                ORDER BY timestamp DESC
            """
            
            cursor.execute(query, (player_name, game_id))
            return cursor.fetchall()
        
        except Error as e:
            logger.error(f"Failed to get game stats: {e}")
            return []


# ============================================================================
# DATA PIPELINE ORCHESTRATOR
# ============================================================================

class Tank01DataPipeline:
    """
    Orchestrates the complete Tank01 → PostgreSQL data pipeline.
    
    This is the glue that connects:
      1. Tank01 API (fetches real-time data)
      2. PostgreSQL (stores data)
      3. FRONTAL LOBE models (uses data for predictions)
      4. Edge Detection (finds trading opportunities)
    """

    def __init__(
        self,
        tank01_api_key: str,
        db_config: Dict[str, str],
        edge_threshold: float = 0.03
    ):
        """
        Initialize data pipeline.
        
        Args:
            tank01_api_key: Tank01 RapidAPI key
            db_config: PostgreSQL connection config
            edge_threshold: Edge detection threshold (default 3%)
        """
        self.tank01_client = Tank01NFLClient(tank01_api_key)
        self.db = Tank01DataLakeConnection(**db_config)
        self.edge_detector = EdgeDetector(threshold=edge_threshold)
        
        self.stats = {
            "props_inserted": 0,
            "stats_inserted": 0,
            "salaries_inserted": 0,
            "injuries_inserted": 0,
            "depth_charts_inserted": 0,
            "edges_detected": 0,
        }

    def initialize(self) -> bool:
        """Initialize pipeline: connect to DB and create tables."""
        if not self.db.connect():
            logger.error("Failed to connect to database")
            return False
        
        if not self.db.create_tables():
            logger.error("Failed to create tables")
            return False
        
        logger.info("✅ Tank01 Data Pipeline initialized")
        return True

    def fetch_and_store_all_data(self, game_date: str) -> bool:
        """
        Fetch all available data from Tank01 and store in PostgreSQL.
        
        Args:
            game_date: Date in format YYYYMMDD
        
        Returns:
            True if successful
        """
        logger.info(f"🔄 Starting Tank01 data fetch for {game_date}...")
        
        try:
            # Fetch betting odds
            logger.info("Fetching betting odds...")
            props = self.tank01_client.get_nfl_betting_odds(game_date, player_props=True)
            if props:
                self.stats["props_inserted"] += self.db.batch_upsert_player_props(props)
            
            # Fetch DFS salaries
            logger.info("Fetching DFS salaries...")
            salaries = self.tank01_client.get_dfs_salaries(game_date)
            if salaries:
                self.stats["salaries_inserted"] += self.db.batch_upsert_dfs_salaries(salaries)
            
            # Fetch injury list
            logger.info("Fetching injury updates...")
            injuries = self.tank01_client.get_nfl_injury_list()
            if injuries:
                self.stats["injuries_inserted"] += self.db.batch_upsert_injuries(injuries)
            
            # Fetch depth charts
            logger.info("Fetching depth charts...")
            depth_charts = self.tank01_client.get_nfl_depth_charts()
            if depth_charts:
                self.stats["depth_charts_inserted"] += self.db.batch_upsert_depth_charts(depth_charts)
            
            logger.info(f"✅ Data fetch complete: {self.stats}")
            return True
        
        except Exception as e:
            logger.error(f"Data fetch failed: {e}")
            return False

    def fetch_live_game_stats(self, game_id: str) -> int:
        """
        Fetch live game statistics for a specific game.
        
        Args:
            game_id: Game ID
        
        Returns:
            Number of records inserted
        """
        try:
            logger.info(f"Fetching live stats for game {game_id}...")
            stats = self.tank01_client.get_nfl_game_box_score(game_id)
            if stats:
                count = self.db.batch_upsert_game_stats(stats)
                self.stats["stats_inserted"] += count
                return count
            return 0
        
        except Exception as e:
            logger.error(f"Failed to fetch live game stats: {e}")
            return 0

    def detect_edges(self, model_predictions: Dict[str, float]) -> List[Dict]:
        """
        Detect edges between model predictions and market odds.
        
        Args:
            model_predictions: Dict of {player_name: predicted_probability}
        
        Returns:
            List of detected edges
        """
        try:
            # Get latest props from database
            cursor = self.db.conn.cursor(cursor_factory=extras.DictCursor)
            cursor.execute("""
                SELECT DISTINCT ON (player_name, stat_type) *
                FROM tank01_player_props
                ORDER BY player_name, stat_type, timestamp DESC
            """)
            
            props_data = cursor.fetchall()
            
            # Convert to PlayerProp objects
            props = []
            for row in props_data:
                prop = PlayerProp(
                    player_name=row['player_name'],
                    player_id=row['player_id'],
                    position=row['position'],
                    team=row['team'],
                    stat_type=row['stat_type'],
                    line=row['line'],
                    over_odds=row['over_odds'],
                    under_odds=row['under_odds'],
                    implied_total=row['implied_total'],
                    timestamp=row['timestamp'].isoformat(),
                    game_id=row['game_id'],
                    game_date=row['game_date'].strftime("%Y%m%d") if row['game_date'] else None,
                )
                props.append(prop)
            
            # Detect edges
            edges = self.edge_detector.detect_edges(props, model_predictions)
            
            if edges:
                self.db.batch_insert_edge_alerts(edges)
                self.stats["edges_detected"] += len(edges)
                logger.info(f"🎯 Detected {len(edges)} edges")
            
            return edges
        
        except Exception as e:
            logger.error(f"Edge detection failed: {e}")
            return []

    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics."""
        tank01_stats = self.tank01_client.get_stats()
        return {
            "data_inserted": self.stats,
            "tank01_api": tank01_stats,
            "timestamp": datetime.now().isoformat(),
        }

    def export_to_json(self, filename: str = "tank01_pipeline_export.json"):
        """Export pipeline statistics and recent data."""
        try:
            edges = self.db.get_latest_edge_alerts(100)
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "pipeline_stats": self.get_pipeline_stats(),
                "edge_alerts": [dict(edge) for edge in edges],
            }
            
            output_dir = Path("./tank01_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = output_dir / filename
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"✅ Exported pipeline data to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None

    def cleanup(self):
        """Clean up resources."""
        self.db.disconnect()
        logger.info("Pipeline cleanup complete")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import os
    
    # Get Tank01 API key
    tank01_key = os.environ.get('TANK01_API_KEY')
    if not tank01_key:
        print("❌ Tank01 API key not found")
        print("Set: export TANK01_API_KEY='your_key'")
        exit(1)
    
    # PostgreSQL configuration (update with your settings)
    db_config = {
        'host': os.environ.get('TANK01_DB_HOST', 'localhost'),
        'port': int(os.environ.get('TANK01_DB_PORT', '5432')),
        'database': os.environ.get('TANK01_DB_NAME', 'sports_data_lake'),
        'user': os.environ.get('TANK01_DB_USER', 'sports_user'),
        'password': os.environ.get('TANK01_DB_PASSWORD', 'sports_password'),
    }
    
    # Initialize pipeline
    pipeline = Tank01DataPipeline(tank01_key, db_config)
    
    if not pipeline.initialize():
        exit(1)
    
    # Fetch data
    today = datetime.now().strftime("%Y%m%d")
    pipeline.fetch_and_store_all_data(today)
    
    # Example edge detection
    predictions = {
        "Travis Kelce": 0.65,
        "Patrick Mahomes": 0.58,
    }
    edges = pipeline.detect_edges(predictions)
    
    # Export results
    pipeline.export_to_json()
    
    # Cleanup
    pipeline.cleanup()
    
    print("\n" + "="*70)
    print("✅ Tank01 Data Pipeline Complete")
    print("="*70)
    print(f"Stats: {pipeline.get_pipeline_stats()}")
