"""
TeamRankings Extractor

Specialized extractor for TeamRankings sports data tables.
Handles authentication, table extraction, and conversion to JSON/Excel.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)


class TeamRankingsExtractor:
    """Extracts data from TeamRankings website tables."""

    # Sport-specific column mappings and keywords
    SPORT_COLUMNS = {
        'mlb': {
            'name': 'MLB - Major League Baseball',
            'common': ['Rank', 'Team', 'Year', 'Last 3', 'Last 1', 'Home', 'Away'],
            'keywords': ['rbi', 'era', 'avg', 'home run', 'strikeout', 'baseball', 'pitcher'],
            'stats': ['RBI', 'ERA', 'AVG', 'HR', 'SO', 'SLG', 'OBP', 'Wins', 'Losses'],
        },
        'nfl': {
            'name': 'NFL - National Football League',
            'common': ['Rank', 'Team', 'W-L', 'PCT', 'PPG', 'PA', 'PD'],
            'keywords': ['pass', 'rush', 'defense', 'touchdown', 'football', 'qb'],
            'stats': ['Wins', 'Losses', 'PPG', 'PA', 'PEFF', 'YDS', 'TO'],
        },
        'wnba': {
            'name': 'WNBA - Women\'s National Basketball Association',
            'common': ['Rank', 'Team', 'W-L', 'PCT', 'PPG', 'PA', 'PD'],
            'keywords': ['basketball', 'women', 'wnba', 'points', 'rebounds', 'assists'],
            'stats': ['Wins', 'Losses', 'PPG', 'PA', 'RPG', 'APG', 'FG%', '3P%'],
        },
        'college_football': {
            'name': 'College Football - NCAA Division I',
            'common': ['Rank', 'Team', 'W-L', 'SOS', 'PPG', 'PA', 'Conference'],
            'keywords': ['college', 'ncaa', 'football', 'conference', 'playoff', 'bowl'],
            'stats': ['Wins', 'Losses', 'PPG', 'PA', 'SOS', 'Conference', 'Playoff'],
        },
        'ncaa': {
            'name': 'NCAA - National Collegiate Athletic Association',
            'common': ['Rank', 'Team', 'W-L', 'Conf', 'PPG', 'PA', 'Strength'],
            'keywords': ['ncaa', 'college', 'conference', 'tournament', 'bracket'],
            'stats': ['Wins', 'Losses', 'Conference', 'PPG', 'PA', 'Tournament'],
        },
        'nba': {
            'name': 'NBA - National Basketball Association',
            'common': ['Rank', 'Team', 'W-L', 'PCT', 'PPG', 'PA', 'PD'],
            'keywords': ['basketball', 'nba', 'points', 'rebounds', 'assists'],
            'stats': ['Wins', 'Losses', 'PPG', 'PA', 'RPG', 'APG', 'FG%', '3P%'],
        },
    }

    def __init__(self, sport: str = 'mlb'):
        """Initialize with sport type."""
        self.sport = sport.lower()
        self.tables_found = []
        self.extracted_data = []

    def extract_from_html_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Extract tables from downloaded HTML file.

        Args:
            filepath: Path to downloaded HTML file

        Returns:
            List of extracted tables with metadata
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return []

        return self.extract_from_html_string(html_content)

    def extract_from_html_string(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract tables from HTML string.

        Args:
            html_content: HTML string content

        Returns:
            List of extracted tables with metadata
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted = []

        # Find all tables
        all_tables = soup.find_all('table')
        logger.info(f"Found {len(all_tables)} tables in HTML")

        for idx, table in enumerate(all_tables):
            table_data = self._extract_table_with_metadata(table, idx)
            if table_data and table_data['row_count'] > 0:
                extracted.append(table_data)

        self.extracted_data = extracted
        return extracted

    def _extract_table_with_metadata(self, table, idx: int) -> Optional[Dict[str, Any]]:
        """Extract table with full metadata."""
        try:
            # Get table headers
            headers = []
            thead = table.find('thead')
            if thead:
                for th in thead.find_all('th'):
                    headers.append(self._clean_text(th.get_text()))
            else:
                # Try first row if no thead
                first_row = table.find('tr')
                if first_row:
                    for th in first_row.find_all(['th', 'td']):
                        headers.append(self._clean_text(th.get_text()))

            if not headers:
                return None

            # Get table body rows
            rows = []
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                row = []
                for td in tr.find_all(['td', 'th']):
                    row.append(self._clean_text(td.get_text()))
                if row:
                    rows.append(row)

            if not rows:
                return None

            # Get table title/caption
            caption = table.find('caption')
            title = caption.get_text() if caption else ''

            # Try to find title from preceding heading
            if not title:
                parent = table.parent
                for sibling in parent.find_all(['h1', 'h2', 'h3', 'h4'], recursive=False):
                    title = self._clean_text(sibling.get_text())
                    break

            # Detect if this is sports data
            is_sports_table = self._is_sports_table(headers, rows)

            return {
                'table_id': f'table_{idx}',
                'title': title,
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
                'col_count': len(headers),
                'is_sports_data': is_sports_table,
                'confidence': self._calculate_confidence(headers, rows),
                'extracted_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error extracting table {idx}: {e}")
            return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean cell text."""
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def detect_sport_type(self, html_content: str) -> str:
        """
        Detect which sport the page contains.

        Returns:
            Sport identifier ('mlb', 'nfl', 'nba', 'wnba', 'college_football', 'ncaa')
        """
        content_lower = html_content.lower()

        # Check page title and meta tags
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.find('title')
        title_text = title.get_text().lower() if title else ''

        sport_scores = {sport: 0 for sport in self.SPORT_COLUMNS.keys()}

        # Score each sport based on keywords and structure
        for sport, config in self.SPORT_COLUMNS.items():
            keywords = config['keywords']
            for keyword in keywords:
                if keyword in title_text:
                    sport_scores[sport] += 2
                if keyword in content_lower:
                    sport_scores[sport] += 1

        # Find highest scoring sport
        detected_sport = max(sport_scores, key=sport_scores.get)
        if sport_scores[detected_sport] > 0:
            logger.info(f"Detected sport: {detected_sport} "
                       f"(confidence: {sport_scores[detected_sport]})")
            return detected_sport

        return 'mlb'  # Default to MLB

    def _is_sports_table(self, headers: List[str], rows: List[List[str]]) -> bool:
        """Check if table contains sports data."""
        sports_keywords = [
            'rank', 'team', 'game', 'win', 'loss', 'point', 'rbi', 'era',
            'avg', 'pct', 'ppg', 'pa', 'stat', 'score', 'player', 'conference',
            'season', 'date', 'opponent', 'w-l', 'record', 'playoff', 'ncaa',
            'college', 'wnba', 'nfl', 'nba', 'mlb', 'rebounds', 'assists',
        ]

        headers_text = ' '.join(headers).lower()
        keyword_count = sum(1 for kw in sports_keywords if kw in headers_text)

        return keyword_count >= 2

    @staticmethod
    def _calculate_confidence(headers: List[str], rows: List[List[str]]) -> float:
        """Calculate data quality confidence score."""
        score = 0.0

        # Check header quality
        if len(headers) >= 3:
            score += 0.2
        if len(headers) >= 5:
            score += 0.1

        # Check row consistency
        if rows:
            first_row_len = len(rows[0])
            consistent = sum(1 for row in rows if len(row) == first_row_len) / len(rows)
            score += consistent * 0.3

            # Check data types
            numeric_cols = 0
            for col_idx in range(min(len(headers), 5)):
                is_numeric = True
                for row in rows[:5]:  # Check first 5 rows
                    if col_idx < len(row):
                        try:
                            float(row[col_idx].replace(',', '').replace('%', ''))
                        except ValueError:
                            is_numeric = False
                            break
                if is_numeric:
                    numeric_cols += 1

            numeric_ratio = numeric_cols / min(len(headers), 5)
            score += numeric_ratio * 0.4

        return min(score, 1.0)

    def convert_to_dataframe(self, table_data: Dict[str, Any]) -> pd.DataFrame:
        """Convert table data to pandas DataFrame."""
        df = pd.DataFrame(table_data['rows'], columns=table_data['headers'])

        # Clean and convert data types
        for col in df.columns:
            df[col] = self._infer_and_convert_column(df[col])

        return df

    @staticmethod
    def _infer_and_convert_column(series: pd.Series) -> pd.Series:
        """Infer and convert column data type."""
        # Try numeric
        try:
            return pd.to_numeric(
                series.astype(str).str.replace(',', '').str.replace('%', ''),
                errors='coerce'
            )
        except:
            pass

        # Try date
        try:
            return pd.to_datetime(series, errors='coerce')
        except:
            pass

        # Keep as string
        return series

    def to_json(self, table_data: Dict[str, Any], filepath: Optional[str] = None) -> str:
        """
        Convert table to JSON.

        Args:
            table_data: Table data dictionary
            filepath: Optional filepath to save

        Returns:
            JSON string
        """
        df = self.convert_to_dataframe(table_data)

        output = {
            'metadata': {
                'title': table_data['title'],
                'extracted_at': table_data['extracted_at'],
                'row_count': table_data['row_count'],
                'col_count': table_data['col_count'],
                'confidence': table_data['confidence'],
                'is_sports_data': table_data['is_sports_data'],
            },
            'headers': table_data['headers'],
            'data': df.to_dict('records'),
        }

        json_str = json.dumps(output, indent=2, default=str)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
            logger.info(f"JSON saved to {filepath}")

        return json_str

    def to_excel(self, table_data: Dict[str, Any], filepath: str,
                sheet_name: str = 'Data') -> None:
        """
        Convert table to Excel.

        Args:
            table_data: Table data dictionary
            filepath: Output filepath
            sheet_name: Sheet name in Excel file
        """
        df = self.convert_to_dataframe(table_data)

        # Create Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Add metadata sheet
            metadata_df = pd.DataFrame({
                'Key': ['Title', 'Extracted At', 'Rows', 'Columns', 'Confidence'],
                'Value': [
                    table_data['title'],
                    table_data['extracted_at'],
                    table_data['row_count'],
                    table_data['col_count'],
                    table_data['confidence'],
                ]
            })
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)

        logger.info(f"Excel saved to {filepath}")

    def to_csv(self, table_data: Dict[str, Any], filepath: str) -> None:
        """Convert table to CSV."""
        df = self.convert_to_dataframe(table_data)
        df.to_csv(filepath, index=False)
        logger.info(f"CSV saved to {filepath}")

    def batch_export(self, output_dir: str, formats: List[str] = None) -> Dict[str, List[str]]:
        """
        Export all extracted tables to multiple formats.

        Args:
            output_dir: Output directory
            formats: List of formats ('json', 'excel', 'csv')

        Returns:
            Dictionary mapping formats to list of saved files
        """
        import os
        if formats is None:
            formats = ['json', 'excel', 'csv']

        os.makedirs(output_dir, exist_ok=True)

        results = {fmt: [] for fmt in formats}

        for idx, table in enumerate(self.extracted_data):
            title = (table.get('title') or f'table_{idx}').lower()
            # Sanitize filename
            title = re.sub(r'[^a-z0-9_]', '_', title)
            title = re.sub(r'_+', '_', title).strip('_')

            base_path = os.path.join(output_dir, title)

            if 'json' in formats:
                json_path = f"{base_path}.json"
                self.to_json(table, json_path)
                results['json'].append(json_path)

            if 'excel' in formats:
                excel_path = f"{base_path}.xlsx"
                self.to_excel(table, excel_path)
                results['excel'].append(excel_path)

            if 'csv' in formats:
                csv_path = f"{base_path}.csv"
                self.to_csv(table, csv_path)
                results['csv'].append(csv_path)

        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of extracted data."""
        return {
            'total_tables': len(self.extracted_data),
            'sports_tables': sum(1 for t in self.extracted_data if t['is_sports_data']),
            'total_rows': sum(t['row_count'] for t in self.extracted_data),
            'high_confidence': sum(1 for t in self.extracted_data if t['confidence'] > 0.7),
            'tables': [
                {
                    'id': t['table_id'],
                    'title': t['title'],
                    'rows': t['row_count'],
                    'cols': t['col_count'],
                    'confidence': t['confidence'],
                }
                for t in self.extracted_data
            ]
        }
