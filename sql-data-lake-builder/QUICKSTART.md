# Quick Start Guide - SQL Data Lake Builder

## What This Tool Does

Extracts sports statistics tables from downloaded websites and converts them into structured JSON, Excel, and SQL formats. Perfect for building predictive models without needing expensive API subscriptions.

**Supported Sports:**
- ⚾ **MLB** - Major League Baseball
- 🏈 **NFL** - National Football League  
- 🏀 **NBA** - National Basketball Association
- 👩‍🏀 **WNBA** - Women's National Basketball Association
- 🏫 **College Football** - NCAA Division I
- 🎓 **NCAA** - College sports (all types)

## Installation

### Step 1: Install Python (if needed)
```bash
# Check if you have Python 3.8+
python3 --version

# If not installed, download from https://www.python.org/
```

### Step 2: Clone or Navigate to Project
```bash
cd /home/hunt/Downloads/FOR\ SQL/sql-data-lake-builder
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt

# OR if you want to install as a package:
pip install -e .
```

## Usage

### Method 1: Full Pipeline (Recommended)

**Step A: Download sports data from TeamRankings**
1. Go to https://www.teamrankings.com
2. Navigate to your sport (MLB, NFL, NBA, etc.)
3. Find the table you want (e.g., "MLB Team RBIs per Game")
4. Right-click → Save Page As... (or Ctrl+S / Cmd+S)
5. Save as HTML file (e.g., `mlb_rbis.html`)

**Step B: Run the tool**
```bash
python cli.py full-pipeline --html mlb_rbis.html
```

**Output:**
- ✅ `output/team_rbis_per_game.json` - Structured JSON
- ✅ `output/team_rbis_per_game.xlsx` - Excel spreadsheet
- ✅ `output/team_rbis_per_game.csv` - CSV format

### Method 2: Individual Commands

**Analyze what's in the HTML:**
```bash
python cli.py analyze --html mlb_rbis.html
```

Output shows:
- Sport detected (MLB, NFL, etc.)
- Number of tables found
- Column names and row counts
- Data quality scores

**Extract with specific formats:**
```bash
# JSON only
python cli.py extract --html mlb_rbis.html --format json

# Excel only
python cli.py extract --html mlb_rbis.html --format excel

# All formats
python cli.py extract --html mlb_rbis.html --format json excel csv
```

**Custom output directory:**
```bash
python cli.py extract --html mlb_rbis.html --output-dir ./my_data
```

### Method 3: Python Script

Use it in your own code:

```python
from src.teamrankings_extractor import TeamRankingsExtractor

# Extract
extractor = TeamRankingsExtractor(sport='mlb')
tables = extractor.extract_from_html_file('mlb_rbis.html')

# Export
results = extractor.batch_export('./output', ['json', 'excel'])

# Summary
summary = extractor.get_summary()
print(f"Found {summary['total_tables']} tables with {summary['total_rows']} rows")
```

## Output Formats Explained

### JSON Format
```json
{
  "metadata": {
    "table_id": "table_0",
    "extracted_at": "2024-01-15T10:30:00",
    "record_count": 30,
    "title": "MLB Team RBIs per Game",
    "sport": "mlb"
  },
  "headers": ["Rank", "Team", "Year", "Last 3", "Last 1", "Home", "Away"],
  "data": [
    {
      "Rank": "1",
      "Team": "Yankees",
      "Year": "5.18",
      "Last 3": "5.33",
      ...
    }
  ]
}
```

**Use for:** APIs, databases, data processing pipelines

### Excel Format
- **Sheet 1 "Data"**: Your extracted table
- **Sheet 2 "Metadata"**: Information about the extraction

**Use for:** Analysis, sharing with non-technical users, pivot tables

### CSV Format
Standard comma-separated values, easy to import into any tool.

**Use for:** SQL imports, data warehouses, spreadsheets

## Real-World Examples

### Example 1: Extract MLB Batting Stats
```bash
# 1. Download from TeamRankings
#    Go to: https://www.teamrankings.com/mlb/stat/team-batting-average
#    Save as: mlb_batting.html

# 2. Run extraction
python cli.py full-pipeline --html mlb_batting.html

# 3. Open output/team_batting_average.xlsx in Excel
# 4. Build your predictive model on batting data
```

### Example 2: Compare NFL Teams Across Seasons
```bash
# Download multiple NFL seasons
python cli.py extract --html nfl_2023.html --output-dir ./2023_data
python cli.py extract --html nfl_2024.html --output-dir ./2024_data

# Now merge and analyze with pandas/SQL
```

### Example 3: Build Database from Multiple Sports
```bash
# Create folders for each sport
mkdir -p ./data/{mlb,nfl,nba,wnba}

# Extract each sport
python cli.py extract --html mlb_data.html --output-dir ./data/mlb
python cli.py extract --html nfl_data.html --output-dir ./data/nfl
python cli.py extract --html nba_data.html --output-dir ./data/nba
python cli.py extract --html wnba_data.html --output-dir ./data/wnba

# Now you have a complete sports data lake!
```

## Next Steps: Building Your Data Lake

### 1. Create a Database
```sql
-- PostgreSQL example
CREATE DATABASE sports_datalake;
CREATE TABLE mlb_teams (
    id SERIAL PRIMARY KEY,
    rank INTEGER,
    team TEXT,
    rbis_per_game DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Import the JSON/CSV
```python
import pandas as pd
import sqlite3

# Read the extracted data
df = pd.read_csv('output/team_rbis_per_game.csv')

# Load into database
conn = sqlite3.connect('sports.db')
df.to_sql('mlb_rbis', conn, if_exists='replace')
conn.close()
```

### 3. Build Queries
```sql
-- Example: Teams with highest RBIs
SELECT Team, DECIMAL(rbis_per_game) as rbis
FROM mlb_rbis
ORDER BY rbis DESC
LIMIT 10;
```

### 4. Create Predictive Models
```python
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import pandas as pd

# Load your extracted data
df = pd.read_csv('output/team_rbis_per_game.csv')

# Build model (example)
X = df[['Last_3', 'Home', 'Away']].values
y = df['Year'].values

model = RandomForestRegressor()
model.fit(X, y)

# Predict!
prediction = model.predict([[5.0, 5.5, 4.8]])
```

## Troubleshooting

### Problem: "No tables found in HTML"
- **Solution:** Make sure you saved the full page, not just part of it
- Try: Right-click → "Save page as" → Select "Webpage, Complete"

### Problem: "Sport not detected"
- **Solution:** Specify it manually
- Try: `python cli.py extract --html file.html --sport mlb`

### Problem: Wrong data in output
- **Solution:** Check with analyze first
- Try: `python cli.py analyze --html file.html` to verify

### Problem: Permission denied
- **Solution:** Ensure output directory is writable
- Try: `chmod 755 ./output` (Mac/Linux)

## Tips & Best Practices

### ✅ DO:
- Download from TeamRankings.com (excellent sports data)
- Test with `analyze` before extracting
- Keep downloaded HTML files for reference
- Name files by sport/year (e.g., `mlb_2024_rbis.html`)

### ❌ DON'T:
- Use copyrighted data without permission
- Run extraction on login-required pages
- Modify downloaded HTML files
- Distribute extracted data commercially without rights

## Getting Help

**Command help:**
```bash
python cli.py --help          # Show all commands
python cli.py extract --help  # Help for extract command
```

**Tutorial:**
```bash
python cli.py tutorial        # Interactive walkthrough
```

## Common Questions

**Q: Can I use other websites?**
A: Yes! The tool works with any HTML table structure. May need tweaking for non-sports sites.

**Q: How often should I update my data?**
A: For predictive models, weekly or monthly updates usually work well. Daily for live betting.

**Q: Can I automate this?**
A: Yes! Save a Python script with your extractions, run via cron job or task scheduler.

**Q: What's the size limit?**
A: Can handle thousands of rows. For millions, consider databases directly.

**Q: Can I use this commercially?**
A: Check the sports league's terms of service. TeamRankings data is for personal use.

## Next: Advanced Features

See `README.md` for:
- Schema generation
- SQL INSERT statements
- Data validation
- ML pipeline formatting
- API response formatting
- Database imports

Happy building! 🚀
