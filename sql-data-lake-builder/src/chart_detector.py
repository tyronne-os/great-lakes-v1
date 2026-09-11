"""
Chart Detector Module

Identifies and extracts tables, charts, and data visualizations from HTML content.
"""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)


class ChartDetector:
    """Detects charts, tables, and data structures in HTML."""

    def __init__(self):
        self.tables_found = []
        self.charts_found = []
        self.patterns = {
            'chart_js': r'new\s+Chart\s*\(',
            'plotly': r'Plotly\.',
            'canvas_svg': r'<canvas|<svg',
            'data_attr': r'data-(?:chart|data|table|values)',
        }

    def detect_from_html(self, html_content: str) -> Dict[str, Any]:
        """
        Detect all potential data sources in HTML.

        Args:
            html_content: HTML string to analyze

        Returns:
            Dictionary with detected tables and charts
        """
        soup = BeautifulSoup(html_content, 'lxml')

        results = {
            'tables': self._detect_tables(soup),
            'data_elements': self._detect_data_elements(soup),
            'script_data': self._detect_script_data(soup),
            'meta_data': self._extract_meta_info(soup),
        }

        logger.info(f"Found {len(results['tables'])} tables, "
                   f"{len(results['data_elements'])} data elements")

        return results

    def _detect_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detect HTML tables in the page."""
        tables = []

        for idx, table in enumerate(soup.find_all('table')):
            table_data = self._extract_table_data(table)
            if table_data['rows'] > 0:  # Only include non-empty tables
                table_data['table_id'] = f"table_{idx}"
                tables.append(table_data)

        return tables

    def _extract_table_data(self, table: Tag) -> Dict[str, Any]:
        """Extract structure and content from a table tag."""
        headers = []
        rows = []
        row_count = 0

        # Extract headers
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                headers.append(self._clean_text(th.get_text()))

        # Extract body rows
        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            row_data = []
            for td in tr.find_all(['td', 'th']):
                row_data.append(self._clean_text(td.get_text()))

            if row_data:
                rows.append(row_data)
                row_count += 1

        # If no headers found, use first row as headers
        if not headers and rows:
            headers = rows.pop(0)

        return {
            'headers': headers,
            'rows': rows,
            'row_count': row_count,
            'col_count': len(headers),
            'title': self._extract_table_title(table),
        }

    def _extract_table_title(self, table: Tag) -> Optional[str]:
        """Extract table title from nearby caption or heading."""
        # Look for caption
        caption = table.find('caption')
        if caption:
            return self._clean_text(caption.get_text())

        # Look for preceding heading
        parent = table.parent
        for sibling in parent.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            return self._clean_text(sibling.get_text())

        return None

    def _detect_data_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detect data in elements with data attributes or specific classes."""
        data_elements = []

        # Look for elements with data attributes
        for elem in soup.find_all(attrs={'data-chart': True}):
            data_elements.append({
                'type': 'data_attribute',
                'content': elem.get('data-chart'),
                'html_class': elem.get('class', []),
            })

        # Look for common chart containers
        for chart_class in ['chart', 'graph', 'visualization', 'data-table']:
            for elem in soup.find_all(class_=chart_class):
                if elem.name in ['div', 'section']:
                    data_elements.append({
                        'type': 'container',
                        'class': chart_class,
                        'id': elem.get('id'),
                        'html': str(elem)[:200],  # First 200 chars
                    })

        return data_elements

    def _detect_script_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detect data embedded in script tags (JSON, arrays, etc)."""
        script_data = []

        for script in soup.find_all('script'):
            content = script.string
            if content:
                # Look for JSON patterns
                json_matches = re.findall(r'\{[^}]*"[^"]*"[^}]*\}', content)
                if json_matches:
                    script_data.append({
                        'type': 'json',
                        'content': json_matches,
                        'script_id': script.get('id'),
                    })

                # Look for array patterns
                array_matches = re.findall(r'\[[^\]]*\]', content)
                if array_matches:
                    script_data.append({
                        'type': 'array',
                        'content': array_matches[:3],  # Limit to first 3
                        'script_id': script.get('id'),
                    })

        return script_data

    def _extract_meta_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata about the page."""
        title = soup.find('title')
        description = soup.find('meta', {'name': 'description'})

        return {
            'title': title.get_text() if title else 'Unknown',
            'description': description.get('content') if description else '',
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters but keep alphanumeric and common punctuation
        text = re.sub(r'[\r\n\t]+', ' ', text)
        return text.strip()

    def detect_sports_data_patterns(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Specifically detect sports-related data patterns.

        Looks for tables with sports keywords and common data formats.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        sports_tables = []

        sports_keywords = [
            'score', 'team', 'player', 'game', 'match', 'win', 'loss',
            'points', 'goal', 'assist', 'stat', 'ranking', 'league',
            'season', 'date', 'opponent', 'record',
        ]

        for idx, table in enumerate(soup.find_all('table')):
            table_text = table.get_text().lower()

            # Check if table contains sports keywords
            if any(keyword in table_text for keyword in sports_keywords):
                table_data = self._extract_table_data(table)
                if table_data['rows'] > 0:
                    table_data['table_id'] = f"sports_{idx}"
                    table_data['confidence'] = self._calculate_sports_confidence(
                        table_data, table_text, sports_keywords
                    )
                    sports_tables.append(table_data)

        return sorted(sports_tables, key=lambda x: x['confidence'], reverse=True)

    @staticmethod
    def _calculate_sports_confidence(table_data: Dict, text: str,
                                     keywords: List[str]) -> float:
        """Calculate confidence score for sports data."""
        score = 0.0

        # Check headers for keywords
        headers_lower = ' '.join(table_data['headers']).lower()
        keyword_matches = sum(1 for kw in keywords if kw in headers_lower)
        score += keyword_matches * 0.15

        # Check table size (sports tables usually have multiple rows/cols)
        if table_data['col_count'] >= 3:
            score += 0.2
        if table_data['row_count'] >= 5:
            score += 0.2

        # Check for numerical data
        numerical_cells = sum(1 for row in table_data['rows']
                            for cell in row if self._is_numeric(cell))
        if table_data['row_count'] > 0:
            numerical_ratio = numerical_cells / (table_data['row_count'] *
                                               table_data['col_count'])
            score += min(numerical_ratio * 0.5, 0.3)

        return min(score, 1.0)

    @staticmethod
    def _is_numeric(value: str) -> bool:
        """Check if a value is numeric."""
        try:
            float(value.replace(',', '').replace('%', '').strip())
            return True
        except ValueError:
            return False
