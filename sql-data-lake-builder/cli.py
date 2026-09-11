#!/usr/bin/env python3
"""
CLI Tool for SQL Data Lake Builder

Extract sports data tables from websites and convert to SQL/JSON/Excel.
"""

import click
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from teamrankings_extractor import TeamRankingsExtractor
    from data_extractor import DataExtractor
    from json_formatter import JSONFormatter
    from chart_detector import ChartDetector
    from prop_gap_scanner import run as run_prop_gap_scan
except ImportError:
    # If imports fail, try from src
    from src.teamrankings_extractor import TeamRankingsExtractor
    from src.data_extractor import DataExtractor
    from src.json_formatter import JSONFormatter
    from src.chart_detector import ChartDetector
    from src.prop_gap_scanner import run as run_prop_gap_scan

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """SQL Data Lake Builder - Extract sports data and generate schemas."""
    pass


@cli.command('scan-gaps')
@click.option('--props', type=click.Path(exists=True), required=True,
              help='RotoWire CSV or JSON export')
@click.option('--defense', type=click.Path(exists=True), required=True,
              help='Team defense CSV or JSON export')
@click.option('--database', type=click.Path(), default='./output/sports_lake.duckdb',
              help='DuckDB database path')
@click.option('--limit', type=int, default=25, show_default=True)
def scan_gaps(props, defense, database, limit):
    """Rank RotoWire props by projection gap and defensive strength."""
    results = run_prop_gap_scan(Path(props), Path(defense), Path(database))
    click.echo(f'✅ Scanned {len(results)} props into {database}')
    for row in results[:limit]:
        click.echo(
            f"{row.get('direction'):5} {row.get('player_name')} "
            f"{row.get('market')} {row.get('line')} -> "
            f"{row.get('adjusted_projection')} "
            f"score={row.get('scan_score')} {row.get('status')}"
        )


@cli.command()
@click.option('--html', type=click.Path(exists=True), required=True,
              help='Path to downloaded HTML file')
@click.option('--sport', type=click.Choice(['mlb', 'nfl', 'nba', 'wnba', 'college_football', 'ncaa']),
              default='mlb', help='Sport type (auto-detected if not specified)')
@click.option('--output-dir', type=click.Path(), default='./output',
              help='Output directory for extracted data')
@click.option('--format', multiple=True, type=click.Choice(['json', 'excel', 'csv']),
              default=['json', 'excel'], help='Export formats')
def extract(html, sport, output_dir, format):
    """Extract tables from downloaded HTML file."""
    click.echo(f"📊 Extracting {sport.upper()} data from {html}...")

    try:
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Extract data
        extractor = TeamRankingsExtractor(sport=sport)
        tables = extractor.extract_from_html_file(html)

        if not tables:
            click.echo("❌ No tables found in HTML file")
            return

        # Auto-detect sport if needed
        with open(html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        detected_sport = extractor.detect_sport_type(html_content)
        click.echo(f"✅ Detected sport: {detected_sport.upper()}")

        # Export to requested formats
        results = extractor.batch_export(output_dir, list(format))

        # Print summary
        summary = extractor.get_summary()
        click.echo(f"\n📈 Extraction Summary:")
        click.echo(f"   Total Tables: {summary['total_tables']}")
        click.echo(f"   Sports Tables: {summary['sports_tables']}")
        click.echo(f"   Total Rows: {summary['total_rows']}")
        click.echo(f"   High Confidence: {summary['high_confidence']}")

        click.echo(f"\n📁 Files saved to: {output_dir}")
        for fmt, files in results.items():
            click.echo(f"   {fmt.upper()}: {len(files)} files")
            for f in files[:3]:  # Show first 3
                click.echo(f"      - {os.path.basename(f)}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        logger.exception(e)


@cli.command()
@click.option('--json', type=click.Path(exists=True), required=True,
              help='Path to extracted JSON file')
@click.option('--db-type', type=click.Choice(['postgresql', 'mysql', 'sqlite', 'tsql']),
              default='postgresql', help='Target database type')
@click.option('--output', type=click.Path(), default='./output/schema.sql',
              help='Output SQL file')
@click.option('--with-data', is_flag=True, help='Include INSERT statements')
def generate_schema(json, db_type, output, with_data):
    """Generate SQL schema from extracted data."""
    click.echo(f"🔧 Generating {db_type.upper()} schema...")

    try:
        formatter = JSONFormatter()
        data = formatter.from_file(json)

        # For this command, we expect the JSON structure from extraction
        click.echo("⚠️  This command needs enhancement for the JSON format you provided.")
        click.echo("   For now, use the full pipeline: extract -> python processing")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        logger.exception(e)


@cli.command()
@click.option('--html', type=click.Path(exists=True), required=True,
              help='Path to downloaded HTML file')
@click.option('--sport', type=click.Choice(['mlb', 'nfl', 'nba', 'wnba', 'college_football', 'ncaa']),
              default=None, help='Sport type (auto-detected if not specified)')
@click.option('--output-dir', type=click.Path(), default='./output',
              help='Output directory')
def full_pipeline(html, sport, output_dir):
    """Complete pipeline: Extract -> Schema -> JSON."""
    click.echo("🚀 Running full data lake pipeline...")

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Step 1: Extract
        click.echo("\n[1/3] Extracting tables from HTML...")
        extractor = TeamRankingsExtractor(sport=sport or 'mlb')

        with open(html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Auto-detect sport
        detected_sport = extractor.detect_sport_type(html_content)
        extractor.sport = detected_sport
        click.echo(f"      ✅ Detected: {detected_sport.upper()}")

        tables = extractor.extract_from_html_string(html_content)
        click.echo(f"      ✅ Found {len(tables)} tables")

        # Step 2: Convert and format
        click.echo("\n[2/3] Converting to JSON and Excel...")
        results = extractor.batch_export(output_dir, ['json', 'excel', 'csv'])

        click.echo(f"      ✅ Created:")
        click.echo(f"         - {len(results['json'])} JSON files")
        click.echo(f"         - {len(results['excel'])} Excel files")
        click.echo(f"         - {len(results['csv'])} CSV files")

        # Step 3: Summary
        click.echo("\n[3/3] Generation Summary...")
        summary = extractor.get_summary()
        click.echo(f"      📊 Tables: {summary['total_tables']}")
        click.echo(f"      📈 Sports Data: {summary['sports_tables']}")
        click.echo(f"      📝 Total Rows: {summary['total_rows']}")
        click.echo(f"      ⭐ Quality (>0.7 confidence): {summary['high_confidence']}")

        click.echo(f"\n✅ Pipeline complete!")
        click.echo(f"📁 Output directory: {output_dir}")
        click.echo(f"\n📋 Files created:")
        for fmt in ['json', 'excel', 'csv']:
            if results[fmt]:
                click.echo(f"\n   {fmt.upper()}:")
                for filepath in results[fmt]:
                    filename = os.path.basename(filepath)
                    size = os.path.getsize(filepath)
                    click.echo(f"      • {filename} ({size} bytes)")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        logger.exception(e)


@cli.command()
@click.option('--html', type=click.Path(exists=True), required=True,
              help='Path to downloaded HTML file')
def analyze(html):
    """Analyze HTML file and show detected tables."""
    click.echo("🔍 Analyzing HTML file...")

    try:
        with open(html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Detect sport
        extractor = TeamRankingsExtractor()
        sport = extractor.detect_sport_type(html_content)
        click.echo(f"🏆 Sport: {sport.upper()}")

        # Extract tables
        tables = extractor.extract_from_html_string(html_content)
        click.echo(f"📊 Found {len(tables)} tables\n")

        # Show table details
        for idx, table in enumerate(tables, 1):
            click.echo(f"Table #{idx}: {table['title']}")
            click.echo(f"   Rows: {table['row_count']}")
            click.echo(f"   Columns: {table['col_count']}")
            click.echo(f"   Confidence: {table['confidence']:.1%}")
            click.echo(f"   Sports Data: {'✅ Yes' if table['is_sports_data'] else '❌ No'}")
            click.echo(f"   Headers: {', '.join(table['headers'][:5])}{'...' if len(table['headers']) > 5 else ''}\n")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        logger.exception(e)


@cli.command()
def version():
    """Show version information."""
    click.echo("SQL Data Lake Builder v1.0.0")
    click.echo("Extracts sports data and generates SQL schemas")


@cli.command()
def tutorial():
    """Show usage tutorial."""
    tutorial_text = """
╔══════════════════════════════════════════════════════════════════════╗
║        SQL Data Lake Builder - Quick Start Tutorial                 ║
╚══════════════════════════════════════════════════════════════════════╝

1. DOWNLOAD WEBSITE DATA
   • Go to https://www.teamrankings.com
   • Find your sport (MLB, NFL, NBA, WNBA, College Football, NCAA)
   • Save the page as HTML (Ctrl+S or Cmd+S)

2. ANALYZE THE HTML
   python cli.py analyze --html downloaded_file.html
   This shows you what tables were found

3. EXTRACT DATA
   python cli.py extract --html downloaded_file.html --format json excel
   • Creates JSON files (for APIs and databases)
   • Creates Excel files (for analysis)
   • Creates CSV files (for spreadsheets)

4. OR RUN FULL PIPELINE
   python cli.py full-pipeline --html downloaded_file.html
   • Detects sport automatically
   • Extracts all tables
   • Generates all output formats

EXAMPLES:
   # Analyze NFL data
   python cli.py analyze --html nfl_stats.html

   # Extract MLB data as JSON and Excel
   python cli.py extract --html mlb_data.html --format json excel

   # Full pipeline for any sport
   python cli.py full-pipeline --html sports_data.html

OUTPUT STRUCTURE:
   output/
   ├── team_rbis_per_game.json      (structured data)
   ├── team_rbis_per_game.xlsx      (spreadsheet)
   ├── team_rbis_per_game.csv       (comma-separated)
   └── ... (more tables)

NEXT STEPS:
   1. Use JSON files to populate your database
   2. Build queries and views on the data
   3. Create predictive models
   4. Expand to official league APIs when ready

Questions? Check README.md for full documentation.
"""
    click.echo(tutorial_text)


if __name__ == '__main__':
    cli()
