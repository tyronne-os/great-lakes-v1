#!/usr/bin/env python3
"""
Example Usage - SQL Data Lake Builder

Shows how to use the tool programmatically in Python scripts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from teamrankings_extractor import TeamRankingsExtractor
from json_formatter import JSONFormatter
import pandas as pd
import json


def example1_basic_extraction():
    """Example 1: Basic extraction from HTML file."""
    print("=" * 60)
    print("Example 1: Basic Extraction")
    print("=" * 60)

    # Initialize extractor
    extractor = TeamRankingsExtractor(sport='mlb')

    # Extract from HTML file
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    print(f"✅ Found {len(tables)} tables\n")

    # Display table info
    for table in tables:
        print(f"Table: {table['title']}")
        print(f"  Rows: {table['row_count']}")
        print(f"  Columns: {table['col_count']}")
        print(f"  Confidence: {table['confidence']:.1%}")
        print(f"  Headers: {table['headers']}\n")


def example2_convert_to_dataframe():
    """Example 2: Convert extracted data to pandas DataFrame."""
    print("=" * 60)
    print("Example 2: Convert to DataFrame")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]
        df = extractor.convert_to_dataframe(table)

        print(f"DataFrame shape: {df.shape}")
        print(f"\nFirst few rows:")
        print(df.head())
        print(f"\nData types:")
        print(df.dtypes)
        print(f"\nBasic statistics:")
        print(df.describe())


def example3_export_multiple_formats():
    """Example 3: Export to multiple formats."""
    print("=" * 60)
    print("Example 3: Export Multiple Formats")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]

        # Export to JSON
        json_str = extractor.to_json(table, 'output_example.json')
        print("✅ JSON exported")

        # Export to Excel
        extractor.to_excel(table, 'output_example.xlsx')
        print("✅ Excel exported")

        # Export to CSV
        extractor.to_csv(table, 'output_example.csv')
        print("✅ CSV exported")

        print("\nFiles created:")
        print("  - output_example.json")
        print("  - output_example.xlsx")
        print("  - output_example.csv")


def example4_batch_export():
    """Example 4: Batch export all tables."""
    print("=" * 60)
    print("Example 4: Batch Export")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    results = extractor.batch_export('./batch_output', ['json', 'excel', 'csv'])

    print("Exported files:")
    for fmt, files in results.items():
        print(f"\n{fmt.upper()}:")
        for f in files:
            print(f"  - {f}")


def example5_format_for_ml():
    """Example 5: Format data for machine learning."""
    print("=" * 60)
    print("Example 5: Format for ML Pipeline")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]
        df = extractor.convert_to_dataframe(table)
        data = df.to_dict('records')

        formatter = JSONFormatter()

        # Format for ML with specific target
        ml_data = formatter.format_for_ml(
            data,
            target_column='Rank',
            feature_columns=['Year', 'Last_3', 'Last_1', 'Home', 'Away']
        )

        print("ML Data Structure:")
        print(f"  Features: {ml_data['features']['columns']}")
        print(f"  Target: {ml_data['target']['column']}")
        print(f"  Records: {ml_data['metadata']['record_count']}")

        # Save for ML
        formatter.to_file(ml_data, 'ml_data.json')
        print("\n✅ ML data saved to ml_data.json")


def example6_format_for_api():
    """Example 6: Format data for API response."""
    print("=" * 60)
    print("Example 6: Format for API")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]
        df = extractor.convert_to_dataframe(table)
        data = df.to_dict('records')

        formatter = JSONFormatter()
        api_response = formatter.format_for_api(data, api_version='2.0')

        print("API Response:")
        print(json.dumps(api_response, indent=2, default=str)[:300] + "...")

        formatter.to_file(api_response, 'api_response.json')
        print("\n✅ API response saved to api_response.json")


def example7_sports_detection():
    """Example 7: Auto-detect sport type."""
    print("=" * 60)
    print("Example 7: Sports Detection")
    print("=" * 60)

    with open('sample_mlb_data.html', 'r') as f:
        html_content = f.read()

    extractor = TeamRankingsExtractor()
    detected_sport = extractor.detect_sport_type(html_content)

    print(f"Detected sport: {detected_sport.upper()}")
    print(f"Sport config: {extractor.SPORT_COLUMNS[detected_sport]['name']}")


def example8_data_quality_check():
    """Example 8: Check data quality."""
    print("=" * 60)
    print("Example 8: Data Quality Check")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]

        print(f"Table: {table['title']}")
        print(f"  Confidence: {table['confidence']:.1%}")
        print(f"  Is Sports Data: {table['is_sports_data']}")
        print(f"  Row Count: {table['row_count']}")
        print(f"  Column Count: {table['col_count']}")


def example9_json_with_schema():
    """Example 9: Format JSON with schema."""
    print("=" * 60)
    print("Example 9: JSON with Schema")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    if tables:
        table = tables[0]
        df = extractor.convert_to_dataframe(table)
        data = df.to_dict('records')

        # Create dtype mapping
        dtypes = {}
        for col in df.columns:
            if df[col].dtype == 'object':
                dtypes[col] = 'TEXT'
            elif df[col].dtype == 'int64':
                dtypes[col] = 'INTEGER'
            else:
                dtypes[col] = 'DECIMAL'

        formatter = JSONFormatter()
        schema_data = formatter.format_with_schema(
            data,
            dtypes,
            table['table_id'],
            {'title': table['title'], 'sport': 'mlb'}
        )

        print("JSON with Schema:")
        print(json.dumps({
            'metadata': schema_data['metadata'],
            'schema': schema_data['schema'],
        }, indent=2, default=str))

        formatter.to_file(schema_data, 'schema_data.json')
        print("\n✅ Schema data saved to schema_data.json")


def example10_get_summary():
    """Example 10: Get extraction summary."""
    print("=" * 60)
    print("Example 10: Extraction Summary")
    print("=" * 60)

    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('sample_mlb_data.html')

    summary = extractor.get_summary()

    print("Extraction Summary:")
    print(f"  Total Tables: {summary['total_tables']}")
    print(f"  Sports Tables: {summary['sports_tables']}")
    print(f"  Total Rows: {summary['total_rows']}")
    print(f"  High Confidence: {summary['high_confidence']}")
    print(f"\nTable Details:")
    for table_info in summary['tables']:
        print(f"  - {table_info['title']} ({table_info['rows']} rows, "
              f"{table_info['confidence']:.1%} confidence)")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQL Data Lake Builder - Usage Examples")
    print("=" * 60 + "\n")

    # Run all examples
    try:
        example1_basic_extraction()
        print()
        example2_convert_to_dataframe()
        print()
        example3_export_multiple_formats()
        print()
        example4_batch_export()
        print()
        example5_format_for_ml()
        print()
        example6_format_for_api()
        print()
        example7_sports_detection()
        print()
        example8_data_quality_check()
        print()
        example9_json_with_schema()
        print()
        example10_get_summary()
        print()
        print("=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
