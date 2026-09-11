"""
FRONTAL LOBE WNBA Heatmap Engine
Generate vision matrices for predictive models and dashboards

Features:
- Percentile-based heatmaps (Baseball Savant style)
- Rolling window performance tracking (5 & 10 game)
- Player comparison matrices
- Heat/cold trend visualization
- Export to PNG for vision model ingestion
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from sklearn.preprocessing import MinMaxScaler
import logging
from typing import List, Tuple, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class WNBAHeatmapEngine:
    """
    Generate WNBA statistics heatmaps for vision models and dashboards
    
    Converts tabular stats into visual matrices for:
    - Computer vision model training
    - Human dashboard visualization
    - Pattern recognition (hot/cold streaks)
    - Percentile-based performance analysis
    """
    
    def __init__(self, output_dir: str = "./wnba_heatmaps"):
        """
        Initialize heatmap engine
        
        Args:
            output_dir: Directory to save generated heatmaps
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scaler = MinMaxScaler()
        
        # Define color schemes
        self.colormap_cool_warm = "RdYlBu_r"  # Red (hot) to Blue (cold)
        self.colormap_percentile = "vlag"  # Cool to warm percentile
        
        logger.info(f"✅ WNBA Heatmap Engine initialized (output: {self.output_dir})")
    
    # ========================================================================
    # DATA FETCHING
    # ========================================================================
    
    def get_wnba_season_stats(self, season: int = 2026) -> pd.DataFrame:
        """
        Fetch WNBA player stats for entire season
        
        Args:
            season: Season year
        
        Returns:
            DataFrame with player stats
        """
        try:
            from frontal_lobe_free_client import FrontalLobeDataStack
            
            client = FrontalLobeDataStack()
            stats = client.get_wnba_stats(stat_type='leaders', season=season)
            
            logger.info(f"✅ Fetched {len(stats)} WNBA players for {season}")
            return stats
        
        except ImportError as e:
            logger.error(f"Failed to import FrontalLobeDataStack: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # PERCENTILE-BASED HEATMAPS (Baseball Savant Style)
    # ========================================================================
    
    def create_percentile_heatmap(
        self,
        players_df: pd.DataFrame,
        stat_columns: List[str],
        title: str = "WNBA Player Stats Heatmap",
        top_n: int = 20,
        figsize: Tuple[int, int] = (14, 10),
        save: bool = True
    ) -> plt.Figure:
        """
        Create Baseball Savant style percentile heatmap
        
        Shows player stats normalized to percentile rankings (0-1 scale):
        - Red: Elite (90th+ percentile)
        - White: Average (50th percentile)
        - Blue: Below Average (10th percentile)
        
        Args:
            players_df: DataFrame with player stats
            stat_columns: Columns to include in heatmap
            title: Chart title
            top_n: Number of top players to display
            figsize: Figure size (width, height)
            save: Whether to save to file
        
        Returns:
            matplotlib Figure object
        """
        try:
            # Select top players by total usage/production
            if 'PTS' in players_df.columns:
                top_players = players_df.nlargest(top_n, 'PTS')
            else:
                top_players = players_df.head(top_n)
            
            # Extract player name column (handle different names)
            name_col = 'PLAYER_NAME' if 'PLAYER_NAME' in top_players.columns else \
                      'PLAYER' if 'PLAYER' in top_players.columns else \
                      top_players.columns[0]
            
            # Create matrix with player names as index
            heatmap_df = top_players.set_index(name_col)[stat_columns].copy()
            
            # Remove rows with NaN
            heatmap_df = heatmap_df.dropna()
            
            # Normalize to percentile (0-1 scale)
            normalized = pd.DataFrame(
                self.scaler.fit_transform(heatmap_df),
                columns=heatmap_df.columns,
                index=heatmap_df.index
            )
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize, dpi=150)
            
            # Create heatmap
            sns.heatmap(
                normalized,
                annot=heatmap_df.round(1),  # Show raw numbers in cells
                fmt='.1f',
                cmap=self.colormap_percentile,  # vlag: cool-to-warm
                linewidths=0.5,
                linecolor='gray',
                cbar_kws={
                    "label": "Percentile Rank (0=Min, 1=Max)",
                    "shrink": 0.8
                },
                ax=ax,
                square=False,
                robust=True
            )
            
            # Styling
            ax.set_title(title, fontsize=18, fontweight='bold', pad=20)
            ax.set_xlabel("Statistics", fontsize=14, fontweight='bold')
            ax.set_ylabel("Players", fontsize=14, fontweight='bold')
            
            # Rotate labels for readability
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
            
            plt.tight_layout()
            
            # Save
            if save:
                filename = f"wnba_percentile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.output_dir / filename
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                logger.info(f"✅ Saved percentile heatmap: {filepath}")
            
            return fig
        
        except Exception as e:
            logger.error(f"Failed to create percentile heatmap: {e}")
            return plt.Figure()
    
    # ========================================================================
    # ROLLING PERFORMANCE TRACKING
    # ========================================================================
    
    def create_rolling_heatmap(
        self,
        player_game_logs: pd.DataFrame,
        player_name: str,
        stat_columns: List[str],
        window: int = 5,
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 6),
        save: bool = True
    ) -> plt.Figure:
        """
        Create rolling average performance heatmap
        
        Tracks player performance over games (e.g., last 5 or last 10 games):
        - Shows trends over time
        - Identifies hot/cold streaks
        - Useful for mid-season projections
        
        Args:
            player_game_logs: DataFrame with game-by-game logs
            player_name: Player name to track
            stat_columns: Stats to track
            window: Rolling window size (5 or 10)
            title: Custom title
            figsize: Figure size
            save: Whether to save
        
        Returns:
            matplotlib Figure object
        """
        try:
            if title is None:
                title = f"{player_name} - Last {window} Games Performance"
            
            # Filter for player
            player_data = player_game_logs[player_game_logs['PLAYER_NAME'] == player_name].copy()
            
            if player_data.empty:
                logger.warning(f"No data found for player: {player_name}")
                return plt.Figure()
            
            # Calculate rolling averages
            rolling_avg = pd.DataFrame(
                player_data[stat_columns].rolling(window=window, min_periods=1).mean().values,
                columns=stat_columns,
                index=range(len(player_data))
            )
            
            # Normalize
            normalized = pd.DataFrame(
                self.scaler.fit_transform(rolling_avg),
                columns=stat_columns,
                index=rolling_avg.index
            )
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize, dpi=150)
            
            # Transpose for better visualization (stats as rows, games as columns)
            sns.heatmap(
                normalized.T,
                cmap=self.colormap_cool_warm,
                linewidths=0.5,
                cbar_kws={"label": "Performance (0=Min, 1=Max)"},
                ax=ax,
                robust=True
            )
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel("Game Number (Recent →)", fontsize=12, fontweight='bold')
            ax.set_ylabel("Statistic", fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            
            # Save
            if save:
                filename = f"wnba_rolling_{player_name.replace(' ', '_')}_{window}g.png"
                filepath = self.output_dir / filename
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                logger.info(f"✅ Saved rolling heatmap: {filepath}")
            
            return fig
        
        except Exception as e:
            logger.error(f"Failed to create rolling heatmap: {e}")
            return plt.Figure()
    
    # ========================================================================
    # PLAYER COMPARISON MATRICES
    # ========================================================================
    
    def create_player_comparison_matrix(
        self,
        players_df: pd.DataFrame,
        player_names: List[str],
        stat_columns: List[str],
        title: str = "WNBA Player Comparison",
        figsize: Tuple[int, int] = (12, 8),
        save: bool = True
    ) -> plt.Figure:
        """
        Create side-by-side comparison heatmap for specific players
        
        Args:
            players_df: DataFrame with all player stats
            player_names: List of players to compare
            stat_columns: Stats to compare
            title: Chart title
            figsize: Figure size
            save: Whether to save
        
        Returns:
            matplotlib Figure object
        """
        try:
            # Find name column
            name_col = 'PLAYER_NAME' if 'PLAYER_NAME' in players_df.columns else \
                      'PLAYER' if 'PLAYER' in players_df.columns else \
                      players_df.columns[0]
            
            # Filter for selected players
            comparison_df = players_df[players_df[name_col].isin(player_names)].copy()
            comparison_df = comparison_df.set_index(name_col)[stat_columns]
            
            # Normalize
            normalized = pd.DataFrame(
                self.scaler.fit_transform(comparison_df),
                columns=stat_columns,
                index=comparison_df.index
            )
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize, dpi=150)
            
            sns.heatmap(
                normalized,
                annot=comparison_df.round(1),
                fmt='.1f',
                cmap=self.colormap_percentile,
                linewidths=1,
                cbar_kws={"label": "Normalized Performance"},
                ax=ax,
                square=False
            )
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Save
            if save:
                player_str = "_vs_".join([p.split()[-1] for p in player_names])
                filename = f"wnba_comparison_{player_str}.png"
                filepath = self.output_dir / filename
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                logger.info(f"✅ Saved comparison heatmap: {filepath}")
            
            return fig
        
        except Exception as e:
            logger.error(f"Failed to create comparison matrix: {e}")
            return plt.Figure()
    
    # ========================================================================
    # CUSTOM STAT FOCUS
    # ========================================================================
    
    def create_custom_stat_heatmap(
        self,
        players_df: pd.DataFrame,
        stat_mapping: dict,
        title: str = "WNBA Custom Stats",
        top_n: int = 15,
        figsize: Tuple[int, int] = (10, 8),
        save: bool = True
    ) -> plt.Figure:
        """
        Create heatmap with custom selected stats
        
        Allows focusing on specific stats relevant to your models
        
        Args:
            players_df: DataFrame with player stats
            stat_mapping: Dict mapping display names to column names
                Example: {"Scoring": "PTS", "Rebounding": "REB", "Efficiency": "TS_PCT"}
            title: Chart title
            top_n: Number of players
            figsize: Figure size
            save: Whether to save
        
        Returns:
            matplotlib Figure object
        """
        try:
            # Find name column
            name_col = 'PLAYER_NAME' if 'PLAYER_NAME' in players_df.columns else \
                      'PLAYER' if 'PLAYER' in players_df.columns else \
                      players_df.columns[0]
            
            # Select top players
            top_players = players_df.nlargest(top_n, 'PTS' if 'PTS' in players_df.columns else players_df.columns[1])
            
            # Extract requested stats
            custom_data = top_players.set_index(name_col)[[v for v in stat_mapping.values() if v in top_players.columns]]
            custom_data.columns = [k for k, v in stat_mapping.items() if v in top_players.columns]
            
            # Normalize
            normalized = pd.DataFrame(
                self.scaler.fit_transform(custom_data),
                columns=custom_data.columns,
                index=custom_data.index
            )
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize, dpi=150)
            
            sns.heatmap(
                normalized,
                annot=custom_data.round(1),
                fmt='.1f',
                cmap=self.colormap_percentile,
                linewidths=0.5,
                cbar_kws={"label": "Percentile"},
                ax=ax
            )
            
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Save
            if save:
                filename = f"wnba_custom_{datetime.now().strftime('%Y%m%d')}.png"
                filepath = self.output_dir / filename
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                logger.info(f"✅ Saved custom heatmap: {filepath}")
            
            return fig
        
        except Exception as e:
            logger.error(f"Failed to create custom heatmap: {e}")
            return plt.Figure()
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def create_all_heatmaps(
        self,
        season: int = 2026,
        show_plots: bool = False
    ) -> dict:
        """
        Generate all available heatmap types
        
        Args:
            season: WNBA season year
            show_plots: Whether to display plots
        
        Returns:
            Dictionary with all generated figures
        """
        logger.info(f"🎨 Generating all WNBA heatmaps for {season}...")
        
        # Fetch data
        stats = self.get_wnba_season_stats(season)
        if stats.empty:
            logger.error("Failed to fetch WNBA stats")
            return {}
        
        figures = {}
        
        try:
            # 1. Percentile heatmap
            logger.info("Generating percentile heatmap...")
            stat_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT']
            stat_cols = [col for col in stat_cols if col in stats.columns]
            
            fig1 = self.create_percentile_heatmap(
                stats,
                stat_cols,
                title=f"WNBA {season} - Top 20 Players Percentile Rankings"
            )
            figures['percentile'] = fig1
            
            # 2. Custom focused stats
            logger.info("Generating custom stats heatmap...")
            custom_stats = {
                'Scoring': 'PTS',
                'Rebounding': 'REB',
                'Assists': 'AST',
                'Steals': 'STL',
                'Blocks': 'BLK'
            }
            
            fig2 = self.create_custom_stat_heatmap(
                stats,
                custom_stats,
                title=f"WNBA {season} - Offensive & Defensive Focus"
            )
            figures['custom'] = fig2
            
            if show_plots:
                plt.show()
            
            logger.info(f"✅ Generated {len(figures)} heatmaps")
            return figures
        
        except Exception as e:
            logger.error(f"Failed to create all heatmaps: {e}")
            return figures
    
    def list_generated_heatmaps(self) -> List[str]:
        """List all generated heatmap files"""
        files = sorted(self.output_dir.glob("*.png"))
        for f in files:
            logger.info(f"  📊 {f.name}")
        return [str(f) for f in files]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FRONTAL LOBE WNBA Heatmap Engine - Test Mode")
    print("=" * 70 + "\n")
    
    engine = WNBAHeatmapEngine(output_dir="./wnba_heatmaps")
    
    try:
        # Generate all heatmaps
        figures = engine.create_all_heatmaps(season=2026, show_plots=False)
        
        print(f"\n✅ Generated {len(figures)} heatmaps\n")
        
        # List files
        print("📊 Generated Files:")
        files = engine.list_generated_heatmaps()
        
        if files:
            print("\n✅ Heatmaps ready for vision model ingestion!")
        else:
            print("\n⚠️ Note: Some heatmaps may require live WNBA data")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)
