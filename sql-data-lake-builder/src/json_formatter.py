"""
JSON Formatter Module

Formats extracted data to JSON with full schema information.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JSONFormatter:
    """Formats data to JSON structures."""

    def __init__(self):
        self.formatted_data = {}

    def format_with_schema(self, extracted_data: Dict[str, Any],
                           dtypes: Dict[str, str],
                           table_id: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format data with schema information.

        Args:
            extracted_data: List of data rows
            dtypes: Dictionary mapping column names to types
            table_id: Unique table identifier
            metadata: Additional metadata

        Returns:
            Formatted dictionary with schema
        """
        if metadata is None:
            metadata = {}

        output = {
            'metadata': {
                'table_id': table_id,
                'extracted_at': datetime.now().isoformat(),
                'record_count': len(extracted_data) if isinstance(extracted_data, list) else 1,
                'source': metadata.get('source', 'unknown'),
                'title': metadata.get('title', ''),
                'sport': metadata.get('sport', 'unknown'),
                **metadata,
            },
            'schema': {
                'fields': self._build_schema_fields(dtypes),
                'primary_key': ['id'],
            },
            'data': extracted_data,
        }

        return output

    @staticmethod
    def _build_schema_fields(dtypes: Dict[str, str]) -> List[Dict[str, Any]]:
        """Build JSON schema field definitions."""
        fields = []

        for col_name, col_type in dtypes.items():
            field = {
                'name': col_name,
                'type': JSONFormatter._map_type_to_json_schema(col_type),
                'nullable': True,
            }
            fields.append(field)

        return fields

    @staticmethod
    def _map_type_to_json_schema(sql_type: str) -> str:
        """Map SQL type to JSON schema type."""
        type_mapping = {
            'INTEGER': 'integer',
            'DECIMAL': 'number',
            'TEXT': 'string',
            'DATE': 'string',
            'TIMESTAMP': 'string',
            'BOOLEAN': 'boolean',
        }
        return type_mapping.get(sql_type, 'string')

    def format_for_api(self, extracted_data: Dict[str, Any],
                       api_version: str = '1.0') -> Dict[str, Any]:
        """
        Format data as API response.

        Args:
            extracted_data: Extracted table data
            api_version: API version

        Returns:
            API-formatted response
        """
        rows = extracted_data.get('data', []) if isinstance(extracted_data, dict) else extracted_data

        return {
            'version': api_version,
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'count': len(rows),
                'records': rows,
            },
            'pagination': {
                'page': 1,
                'page_size': len(rows),
                'total': len(rows),
            },
        }

    def format_for_ml(self, extracted_data: List[Dict[str, Any]],
                     target_column: Optional[str] = None,
                     feature_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Format data for machine learning pipelines.

        Args:
            extracted_data: List of records
            target_column: Column to predict
            feature_columns: Columns to use as features

        Returns:
            ML-formatted data
        """
        if not extracted_data:
            return {'features': [], 'target': [], 'metadata': {}}

        # Infer if not provided
        if feature_columns is None:
            first_record = extracted_data[0]
            feature_columns = list(first_record.keys())
            if target_column and target_column in feature_columns:
                feature_columns.remove(target_column)

        features = []
        target = []

        for record in extracted_data:
            feature_row = [record.get(col) for col in feature_columns]
            features.append(feature_row)

            if target_column:
                target.append(record.get(target_column))

        return {
            'features': {
                'columns': feature_columns,
                'data': features,
            },
            'target': {
                'column': target_column,
                'data': target if target_column else None,
            },
            'metadata': {
                'record_count': len(extracted_data),
                'feature_count': len(feature_columns),
                'prepared_at': datetime.now().isoformat(),
            },
        }

    def format_for_datawarehouse(self, extracted_data: Dict[str, Any],
                                 table_name: str,
                                 partition_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Format data for data warehouse ingestion.

        Args:
            extracted_data: Extracted data
            table_name: Target table name
            partition_columns: Columns to partition by

        Returns:
            Data warehouse formatted structure
        """
        rows = extracted_data.get('data', []) if isinstance(extracted_data, dict) else extracted_data

        output = {
            'table_name': table_name,
            'operation': 'INSERT',
            'metadata': {
                'ingestion_time': datetime.now().isoformat(),
                'record_count': len(rows),
                'partition_columns': partition_columns or [],
            },
            'records': rows,
        }

        if partition_columns:
            output['partitions'] = self._extract_partitions(rows, partition_columns)

        return output

    @staticmethod
    def _extract_partitions(rows: List[Dict[str, Any]],
                           partition_columns: List[str]) -> Dict[str, List[Any]]:
        """Extract partition values from data."""
        partitions = {col: [] for col in partition_columns}

        for row in rows:
            for col in partition_columns:
                val = row.get(col)
                if val and val not in partitions[col]:
                    partitions[col].append(val)

        return partitions

    def format_to_json_lines(self, extracted_data: List[Dict[str, Any]]) -> str:
        """
        Format data as JSON Lines (one record per line).

        Args:
            extracted_data: List of records

        Returns:
            JSON Lines string
        """
        lines = [json.dumps(record, default=str) for record in extracted_data]
        return '\n'.join(lines)

    def format_to_nested(self, extracted_data: List[Dict[str, Any]],
                        group_by: str,
                        nested_key: str = 'records') -> Dict[str, Any]:
        """
        Format data with nested grouping.

        Args:
            extracted_data: List of records
            group_by: Column to group by
            nested_key: Key name for nested records

        Returns:
            Grouped nested structure
        """
        grouped = {}

        for record in extracted_data:
            group_val = record.get(group_by)
            if group_val not in grouped:
                grouped[group_val] = {nested_key: []}
            grouped[group_val][nested_key].append(record)

        return grouped

    def validate_json_schema(self, data: Dict[str, Any],
                            schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data against JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required = schema.get('required', [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check field types
        properties = schema.get('properties', {})
        for field_name, field_schema in properties.items():
            if field_name in data:
                expected_type = field_schema.get('type')
                actual_value = data[field_name]
                if not self._validate_type(actual_value, expected_type):
                    errors.append(f"Field {field_name}: expected {expected_type}, "
                                f"got {type(actual_value).__name__}")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """Validate if value matches expected type."""
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict,
        }

        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True

    def to_file(self, data: Dict[str, Any], filepath: str,
                pretty: bool = True) -> None:
        """Save JSON to file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2 if pretty else None, default=str)
        logger.info(f"JSON saved to {filepath}")

    def from_file(self, filepath: str) -> Dict[str, Any]:
        """Load JSON from file."""
        with open(filepath, 'r') as f:
            return json.load(f)
