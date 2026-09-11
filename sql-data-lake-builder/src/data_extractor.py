"""
Data Extractor Module

Extracts, cleans, and normalizes data from detected tables and charts.
"""

import re
from typing import List, Dict, Any, Union, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extracts and normalizes data from structured sources."""

    def __init__(self):
        self.extracted_data = {}
        self.type_mappings = {}

    def extract_from_tables(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract and normalize data from detected tables.

        Args:
            tables: List of table dictionaries from ChartDetector

        Returns:
            Dictionary with extracted and cleaned data
        """
        extracted = {}

        for table in tables:
            table_id = table.get('table_id', 'unknown')
            table_name = self._generate_table_name(
                table.get('title') or table_id
            )

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(table['rows'], columns=table['headers'])

            # Clean and normalize
            df = self._clean_dataframe(df)

            extracted[table_name] = {
                'id': table_id,
                'title': table.get('title', ''),
                'data': df.to_dict('records'),
                'columns': list(df.columns),
                'dtypes': self._infer_dtypes(df).to_dict(),
                'rows': len(df),
                'stats': self._calculate_stats(df),
            }

        self.extracted_data = extracted
        return extracted

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize a DataFrame."""
        # Remove completely empty rows/columns
        df = df.dropna(how='all')
        df = df.loc[:, (df != '').any(axis=0)]

        # Clean individual cells
        for col in df.columns:
            df[col] = df[col].apply(self._clean_cell)

        # Remove duplicate rows
        df = df.drop_duplicates()

        return df.reset_index(drop=True)

    @staticmethod
    def _clean_cell(value: Any) -> str:
        """Clean individual cell values."""
        if not isinstance(value, str):
            value = str(value)

        # Strip whitespace
        value = value.strip()

        # Remove common noise
        value = re.sub(r'[\r\n\t]+', ' ', value)
        value = re.sub(r'\s+', ' ', value)

        return value

    @staticmethod
    def _generate_table_name(title: str) -> str:
        """Generate a valid SQL table name from a title."""
        # Convert to lowercase
        name = title.lower()

        # Replace spaces and special chars with underscores
        name = re.sub(r'[^a-z0-9_]', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)

        # Ensure it starts with letter or underscore
        if name and name[0].isdigit():
            name = 't_' + name

        return name or 'table_unknown'

    def _infer_dtypes(self, df: pd.DataFrame) -> pd.Series:
        """Infer data types for DataFrame columns."""
        dtypes = {}

        for col in df.columns:
            dtypes[col] = self._infer_column_type(df[col])

        return pd.Series(dtypes)

    @staticmethod
    def _infer_column_type(series: pd.Series) -> str:
        """Infer the data type of a series."""
        # Remove empty values
        non_empty = series[series.astype(str).str.strip() != '']

        if len(non_empty) == 0:
            return 'TEXT'

        # Check for numeric
        numeric_count = 0
        for val in non_empty:
            try:
                float(str(val).replace(',', '').replace('%', '').strip())
                numeric_count += 1
            except ValueError:
                pass

        if numeric_count / len(non_empty) > 0.8:
            # Check if it has decimal points
            has_decimal = any('.' in str(val) for val in non_empty)
            return 'DECIMAL' if has_decimal else 'INTEGER'

        # Check for date
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
            r'\d{1,2}-\w+-\d{4}',  # DD-MON-YYYY
        ]
        date_count = 0
        for val in non_empty:
            if any(re.match(pattern, str(val)) for pattern in date_patterns):
                date_count += 1

        if date_count / len(non_empty) > 0.8:
            return 'DATE'

        # Default to TEXT
        return 'TEXT'

    @staticmethod
    def _calculate_stats(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistics for a DataFrame."""
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'empty_cells': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum()),
        }

        return stats

    def extract_with_schema(self, tables: List[Dict[str, Any]],
                           schema_hints: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Extract data with optional schema hints for better type inference.

        Args:
            tables: List of table dictionaries
            schema_hints: Optional dict mapping column names to data types

        Returns:
            Extracted data with applied schema hints
        """
        extracted = self.extract_from_tables(tables)

        if schema_hints:
            extracted = self._apply_schema_hints(extracted, schema_hints)

        return extracted

    @staticmethod
    def _apply_schema_hints(extracted: Dict[str, Any],
                           hints: Dict[str, str]) -> Dict[str, Any]:
        """Apply schema hints to extracted data."""
        for table_name, table_data in extracted.items():
            for col in table_data['columns']:
                if col in hints:
                    table_data['dtypes'][col] = hints[col]

        return extracted

    def validate_data_quality(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data quality and return a quality report.

        Returns:
            Quality metrics for each table
        """
        quality_report = {}

        for table_name, table_data in extracted.items():
            df = pd.DataFrame(table_data['data'])

            quality_report[table_name] = {
                'completeness': self._calculate_completeness(df),
                'uniqueness': self._calculate_uniqueness(df),
                'consistency': self._calculate_consistency(df),
                'validity': self._calculate_validity(df, table_data['dtypes']),
                'overall_score': 0.0,
            }

            # Calculate overall score
            scores = [
                quality_report[table_name]['completeness'],
                quality_report[table_name]['uniqueness'],
                quality_report[table_name]['consistency'],
                quality_report[table_name]['validity'],
            ]
            quality_report[table_name]['overall_score'] = sum(scores) / len(scores)

        return quality_report

    @staticmethod
    def _calculate_completeness(df: pd.DataFrame) -> float:
        """Calculate completeness score (% of non-null values)."""
        if len(df) == 0:
            return 0.0
        total_cells = len(df) * len(df.columns)
        non_null = df.count().sum()
        return non_null / total_cells

    @staticmethod
    def _calculate_uniqueness(df: pd.DataFrame) -> float:
        """Calculate uniqueness score."""
        if len(df) == 0:
            return 0.0
        unique_rows = len(df.drop_duplicates())
        return unique_rows / len(df)

    @staticmethod
    def _calculate_consistency(df: pd.DataFrame) -> float:
        """Calculate consistency score."""
        # Check if columns have consistent types
        score = 0.0
        for col in df.columns:
            # Convert to string and check pattern consistency
            str_col = df[col].astype(str)
            if len(str_col) > 0:
                # Simple heuristic: consistent if all similar length
                lengths = str_col.str.len()
                if len(lengths) > 1:
                    mean_len = lengths.mean()
                    std_len = lengths.std()
                    if std_len < mean_len * 0.5:  # Low variance
                        score += 1.0 / len(df.columns)

        return min(score, 1.0)

    @staticmethod
    def _calculate_validity(df: pd.DataFrame, dtypes: Dict[str, str]) -> float:
        """Calculate validity score based on expected types."""
        valid = 0
        total = 0

        for col in df.columns:
            expected_type = dtypes.get(col, 'TEXT')
            total += len(df)

            for val in df[col]:
                if DataExtractor._is_valid_type(val, expected_type):
                    valid += 1

        return valid / total if total > 0 else 0.0

    @staticmethod
    def _is_valid_type(value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected type."""
        str_val = str(value).strip()

        if not str_val or str_val.lower() in ['nan', 'none', 'null', '']:
            return True  # Allow empty values

        if expected_type == 'INTEGER':
            try:
                int(str_val.replace(',', ''))
                return True
            except ValueError:
                return False

        elif expected_type == 'DECIMAL':
            try:
                float(str_val.replace(',', '').replace('%', ''))
                return True
            except ValueError:
                return False

        elif expected_type == 'DATE':
            patterns = [
                r'^\d{4}-\d{2}-\d{2}$',
                r'^\d{1,2}/\d{1,2}/\d{4}$',
                r'^\d{1,2}-\w+-\d{4}$',
            ]
            return any(re.match(pattern, str_val) for pattern in patterns)

        return True  # TEXT type accepts everything
