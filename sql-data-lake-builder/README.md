# SQL Data Lake Builder - Sports Data Extraction Tool

An intelligent tool that extracts sports data from downloaded websites and automatically generates SQL schemas, JSON outputs, and data lake structures for predictive modeling.

## Features

- **Automatic Chart Detection**: Identifies tables, charts, and data visualizations in HTML
- **Smart Data Extraction**: Extracts structured data from various chart formats
- **Schema Generation**: Auto-generates SQL CREATE TABLE statements
- **JSON Export**: Converts extracted data to JSON for easy integration
- **Data Validation**: Validates data types and relationships
- **Local Agent**: Runs as a standalone CLI or Python module

## Architecture

```
sql-data-lake-builder/
├── src/
│   ├── __init__.py
│   ├── main.py                      # Entry point
│   ├── chart_detector.py            # Identifies charts/tables in HTML
│   ├── data_extractor.py            # Extracts data from charts
│   ├── schema_generator.py          # Generates SQL schemas
│   ├── json_formatter.py            # Formats data to JSON
│   ├── validators.py                # Validates extracted data
│   └── config.py                    # Configuration management
├── examples/
│   ├── sample_sports_data.html      # Example sports website
│   ├── config.yaml                  # Configuration template
│   └── output_example.json          # Example output
├── output/                          # Generated schemas and data
│   ├── schemas/                     # SQL CREATE statements
│   ├── data/                        # JSON data files
│   └── reports/                     # Analysis reports
├── tests/
│   ├── test_extractor.py
│   └── test_schema.py
├── requirements.txt
├── setup.py
└── cli.py                           # CLI interface
```

## Quick Start

```bash
# 1. Extract data from downloaded website
python cli.py extract --html /path/to/downloaded/site.html

# 2. Generate SQL schema
python cli.py schema --data output/data/extracted.json

# 3. View results
cat output/schemas/sports_data.sql
cat output/data/sports_data.json
```

## Usage Examples

See individual module documentation for detailed usage.

## Data Flow

```
Downloaded Website HTML
         ↓
    Chart Detector (finds tables, charts)
         ↓
    Data Extractor (pulls values, headers)
         ↓
    Validator (checks types, consistency)
         ↓
    Schema Generator (creates SQL)
    + JSON Formatter (creates JSON)
         ↓
    Output Files (ready for data lake)
```

## Why This Tool?

- **No API needed**: Works with downloaded HTML
- **Free**: No paid subscriptions required
- **Automated**: Intelligently detects and extracts data
- **Ready for ML**: JSON output works directly with ML pipelines
- **Flexible**: Handles various data formats and structures
