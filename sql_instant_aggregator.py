"""
🔍 SQL INSTANT SPORTS DATA AGGREGATOR
Converts TeamRankings HTML pages → Auto-Detects Schema → Prediction Features
For: Gemini Flash, Qwen, Vertex AI Model Integration

Workflow:
1. Ingest TeamRankings HTML pages (from /media/hunt/writable/THE_FOOTBALL_PROPHET_PROJECT/teamrankings_mirror/)
2. Auto-detect table schemas (columns, data types, metrics)
3. Convert stats → prediction features
4. Format for AI models (Gemini Flash, Qwen, Vertex)
5. Display daily opportunities panel (by sport)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
from enum import Enum
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DETECTION
# ============================================================================

class DataType(Enum):
    NUMERIC = "numeric"
    PERCENTAGE = "percentage"
    RANK = "rank"
    PLAYER_NAME = "player_name"
    TEAM_NAME = "team_name"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


@dataclass
class ColumnSchema:
    """Detected table column"""
    name: str
    display_name: str
    data_type: DataType
    sample_values: List[str]
    null_count: int
    unique_count: int
    
    def to_dict(self):
        return {
            "name": self.name,
            "display_name": self.display_name,
            "data_type": self.data_type.value,
            "sample_values": self.sample_values[:3],
            "null_count": self.null_count,
            "unique_count": self.unique_count
        }


@dataclass
class TableSchema:
    """Detected HTML table schema"""
    table_id: str
    sport: str
    category: str
    columns: List[ColumnSchema]
    row_count: int
    source_file: str
    timestamp: str
    
    def to_dict(self):
        return {
            "table_id": self.table_id,
            "sport": self.sport,
            "category": self.category,
            "columns": [c.to_dict() for c in self.columns],
            "row_count": self.row_count,
            "source_file": self.source_file,
            "timestamp": self.timestamp
        }


class SchemaDetector:
    """Auto-detect schema from HTML tables"""
    
    def __init__(self):
        self.patterns = {
            'percentage': re.compile(r'^\d+\.?\d*%$'),
            'integer': re.compile(r'^\d+$'),
            'float': re.compile(r'^\d+\.\d+$'),
            'rank': re.compile(r'^#?\d+$'),
            'player_name': re.compile(r'^[A-Z][a-z]+ [A-Z][a-z]+'),
            'team_abbr': re.compile(r'^[A-Z]{2,3}$')
        }
    
    def detect_type(self, values: List[str]) -> DataType:
        """Detect column data type"""
        non_null = [str(v).strip() for v in values if v and str(v).strip()]
        if not non_null:
            return DataType.UNKNOWN
        
        sample = non_null[0]
        
        if self.patterns['percentage'].match(sample):
            return DataType.PERCENTAGE
        elif self.patterns['rank'].match(sample):
            return DataType.RANK
        elif self.patterns['integer'].match(sample) or self.patterns['float'].match(sample):
            return DataType.NUMERIC
        elif self.patterns['player_name'].match(sample):
            return DataType.PLAYER_NAME
        elif self.patterns['team_abbr'].match(sample):
            return DataType.TEAM_NAME
        
        return DataType.CATEGORICAL
    
    def detect_schema(self, df: pd.DataFrame, source_file: str, sport: str, category: str) -> TableSchema:
        """Detect full table schema"""
        
        columns = []
        for col in df.columns:
            col_values = df[col].astype(str).tolist()
            col_type = self.detect_type(col_values)
            
            columns.append(ColumnSchema(
                name=str(col),
                display_name=str(col).replace('_', ' ').title(),
                data_type=col_type,
                sample_values=col_values[:5],
                null_count=df[col].isna().sum(),
                unique_count=df[col].nunique()
            ))
        
        table_id = f"{sport.lower()}_{category.lower()}_{datetime.utcnow().strftime('%H%M%S')}"
        
        return TableSchema(
            table_id=table_id,
            sport=sport,
            category=category,
            columns=columns,
            row_count=len(df),
            source_file=source_file,
            timestamp=datetime.utcnow().isoformat()
        )


# ============================================================================
# PAGE INGESTION
# ============================================================================

class TeamRankingsIngester:
    """Extract tables from TeamRankings HTML files"""
    
    def __init__(self):
        self.detector = SchemaDetector()
    
    def ingest_html_file(self, html_path: Path) -> List[Tuple[pd.DataFrame, Dict]]:
        """Extract all tables from single HTML file"""
        
        results = []
        try:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Get page context
            title = soup.find('title')
            page_title = title.text if title else "Unknown"
            sport = self._extract_sport(html_path, page_title)
            
            # Find all tables
            tables = soup.find_all('table')
            
            for i, table in enumerate(tables):
                try:
                    # Convert to DataFrame
                    dfs = pd.read_html(str(table))
                    if dfs:
                        df = dfs[0]
                        if len(df) > 0:  # Only valid tables
                            category = self._extract_category(page_title, df.columns.tolist())
                            metadata = {
                                "page_title": page_title,
                                "source_file": html_path.name,
                                "sport": sport,
                                "category": category,
                                "table_index": i
                            }
                            results.append((df, metadata))
                
                except Exception as e:
                    pass  # Skip malformed tables
        
        except Exception as e:
            logger.warning(f"Failed to ingest {html_path.name}: {e}")
        
        return results
    
    @staticmethod
    def _extract_sport(path: Path, title: str) -> str:
        """Extract sport from file path or title"""
        path_str = str(path).lower()
        title_lower = title.lower()
        
        if 'nfl' in path_str or 'nfl' in title_lower:
            return "NFL"
        elif 'nba' in path_str or 'nba' in title_lower:
            return "NBA"
        elif 'mlb' in path_str or 'mlb' in title_lower:
            return "MLB"
        elif 'nhl' in path_str or 'nhl' in title_lower:
            return "NHL"
        elif 'ncf' in path_str:
            return "NCAA Football"
        elif 'ncb' in path_str:
            return "NCAA Basketball"
        elif 'wnba' in path_str or 'wnba' in title_lower:
            return "WNBA"
        return "Unknown"
    
    @staticmethod
    def _extract_category(title: str, columns: List[str]) -> str:
        """Extract category: stats, odds, props, rankings"""
        title_lower = title.lower()
        cols_lower = ' '.join([str(c).lower() for c in columns])
        
        if any(x in title_lower for x in ['odds', 'spread', 'line']):
            return "odds"
        elif any(x in title_lower for x in ['prop', 'player']):
            return "props"
        elif any(x in title_lower for x in ['rank', 'rating']):
            return "rankings"
        elif any(x in title_lower for x in ['injury', 'status']):
            return "injuries"
        else:
            return "stats"


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

class PredictionFeatureExtractor:
    """Convert stats tables → ML features"""
    
    def extract_features(self, df: pd.DataFrame, schema: TableSchema) -> Dict[str, Any]:
        """Generate prediction features from DataFrame"""
        
        features = {
            "metadata": {
                "table_id": schema.table_id,
                "sport": schema.sport,
                "category": schema.category,
                "rows": schema.row_count,
                "columns": len(schema.columns)
            },
            "numeric_summary": {},
            "top_entities": [],
            "key_metrics": {}
        }
        
        # Numeric aggregations
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            try:
                features["numeric_summary"][str(col)] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                }
            except:
                pass
        
        # Extract top entities (teams/players)
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if likely a team/player name column
                if any(x in str(col).lower() for x in ['team', 'player', 'name']):
                    features["top_entities"].extend(df[col].unique()[:5].tolist())
        
        # Key sport-specific metrics
        features["key_metrics"] = self._extract_sport_metrics(df, schema.sport)
        
        return features
    
    @staticmethod
    def _extract_sport_metrics(df: pd.DataFrame, sport: str) -> Dict:
        """Extract sport-specific metrics"""
        metrics = {}
        cols_lower = [c.lower() for c in df.columns]
        
        if sport in ["NFL", "NCAA Football"]:
            for col in df.columns:
                if any(x in col.lower() for x in ['pass', 'rush', 'total_yards', 'ppg', 'points']):
                    try:
                        metrics[col] = float(df[col].mean()) if df[col].dtype in [np.float64, np.int64] else None
                    except:
                        pass
        
        elif sport in ["NBA", "WNBA", "NCAA Basketball"]:
            for col in df.columns:
                if any(x in col.lower() for x in ['ppg', 'rpg', 'apg', 'fg%', 'ts%', '3p%']):
                    try:
                        metrics[col] = float(df[col].mean()) if df[col].dtype in [np.float64, np.int64] else None
                    except:
                        pass
        
        elif sport in ["MLB"]:
            for col in df.columns:
                if any(x in col.lower() for x in ['avg', 'hr', 'rbi', 'era', 'ops', 'ops+']):
                    try:
                        metrics[col] = float(df[col].mean()) if df[col].dtype in [np.float64, np.int64] else None
                    except:
                        pass
        
        return metrics


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class SQLInstantAggregator:
    """Main orchestrator: HTML → Schema → Features → Panel"""
    
    def __init__(self, mirror_path: Path):
        self.mirror_path = mirror_path
        self.ingester = TeamRankingsIngester()
        self.extractor = PredictionFeatureExtractor()
        self.schemas: List[TableSchema] = []
        self.features: List[Dict] = []
    
    def process_mirror_directory(self) -> Dict:
        """Process all HTML files in TeamRankings mirror"""
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing TeamRankings mirror: {self.mirror_path}")
        logger.info('='*80)
        
        html_files = list(self.mirror_path.glob('**/*.html'))
        logger.info(f"Found {len(html_files)} HTML files\n")
        
        tables_found = 0
        errors = 0
        
        for i, html_file in enumerate(html_files[:50]):  # Process first 50 files
            tables = self.ingester.ingest_html_file(html_file)
            
            for df, metadata in tables:
                try:
                    # Detect schema
                    schema = self.ingester.detector.detect_schema(
                        df,
                        html_file.name,
                        metadata['sport'],
                        metadata['category']
                    )
                    
                    # Extract features
                    features = self.extractor.extract_features(df, schema)
                    
                    self.schemas.append(schema)
                    self.features.append(features)
                    tables_found += 1
                    
                    if tables_found % 10 == 0:
                        logger.info(f"✅ Processed {tables_found} tables...")
                
                except Exception as e:
                    errors += 1
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "html_files_scanned": len(html_files[:50]),
            "tables_extracted": tables_found,
            "errors": errors,
            "schemas": [s.to_dict() for s in self.schemas[:10]],  # Return first 10
            "features": self.features[:10]
        }
        
        return result
    
    def print_report(self):
        """Print aggregation report"""
        print("\n" + "="*80)
        print("📊 SQL INSTANT SPORTS DATA AGGREGATOR - REPORT")
        print("="*80)
        
        print(f"\n✅ Total Schemas Detected: {len(self.schemas)}")
        print(f"✅ Total Features Extracted: {len(self.features)}")
        
        # By sport
        sport_counts = {}
        for schema in self.schemas:
            sport_counts[schema.sport] = sport_counts.get(schema.sport, 0) + 1
        
        print("\n🏈 By Sport:")
        for sport, count in sorted(sport_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {sport}: {count} tables")
        
        # By category
        cat_counts = {}
        for schema in self.schemas:
            cat_counts[schema.category] = cat_counts.get(schema.category, 0) + 1
        
        print("\n📋 By Category:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {cat}: {count} tables")
        
        # Sample schema
        if self.schemas:
            print("\n🔍 Sample Schema (First Table):")
            schema = self.schemas[0]
            print(f"   Table ID: {schema.table_id}")
            print(f"   Sport: {schema.sport} | Category: {schema.category}")
            print(f"   Rows: {schema.row_count} | Columns: {len(schema.columns)}")
            print(f"   Columns:")
            for col in schema.columns[:5]:
                print(f"     - {col.display_name}: {col.data_type.value} ({col.unique_count} unique)")
        
        print("\n" + "="*80 + "\n")


# ============================================================================
# OPPORTUNITIES PANEL (Backend)
# ============================================================================

class DailyOpportunitiesPanel:
    """Backend panel: daily opportunities by sport"""
    
    def __init__(self):
        self.opportunities = {}
    
    def add_schema_opportunity(self, schema: TableSchema, features: Dict):
        """Add discovered schema as opportunity"""
        sport = schema.sport
        if sport not in self.opportunities:
            self.opportunities[sport] = []
        
        self.opportunities[sport].append({
            "table_id": schema.table_id,
            "category": schema.category,
            "rows": schema.row_count,
            "source": schema.source_file,
            "key_metrics": list(features.get("key_metrics", {}).keys())[:5]
        })
    
    def print_panel(self):
        """Display daily opportunities"""
        print("\n" + "="*80)
        print("🎯 DAILY OPPORTUNITIES PANEL (Backend)")
        print("="*80)
        print(f"Generated: {datetime.utcnow().isoformat()}\n")
        
        for sport in sorted(self.opportunities.keys()):
            opps = self.opportunities[sport]
            print(f"\n🏈 {sport} ({len(opps)} data opportunities)")
            print("-" * 80)
            
            for opp in opps[:3]:
                print(f"\n  📊 {opp['table_id']}")
                print(f"     Category: {opp['category']} | Rows: {opp['rows']}")
                print(f"     Key Metrics: {', '.join(opp['key_metrics'])}")
        
        print("\n" + "="*80 + "\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Initialize with USB path
    mirror_path = Path("/media/hunt/writable/THE_FOOTBALL_PROPHET_PROJECT/teamrankings_mirror")
    
    if not mirror_path.exists():
        logger.error(f"Mirror path not found: {mirror_path}")
        exit(1)
    
    # Create aggregator
    aggregator = SQLInstantAggregator(mirror_path)
    
    # Process all files
    result = aggregator.process_mirror_directory()
    
    # Print report
    aggregator.print_report()
    
    # Print opportunities panel
    panel = DailyOpportunitiesPanel()
    for i, (schema, features) in enumerate(zip(aggregator.schemas, aggregator.features)):
        panel.add_schema_opportunity(schema, features)
    panel.print_panel()
    
    # Save results to JSON
    output_file = Path("/home/hunt/Downloads/FOR SQL") / "aggregator_results.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    logger.info(f"✅ Results saved to {output_file}")
