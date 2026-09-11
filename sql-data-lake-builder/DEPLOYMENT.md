# Deployment Guide - SQL Data Lake Builder

## Table of Contents
1. [Local Setup](#local-setup)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Database Integration](#database-integration)
5. [Scheduling](#scheduling)
6. [Monitoring](#monitoring)

---

## Local Setup

### Prerequisites
- Python 3.8 or higher
- pip or conda
- 100MB free disk space

### Installation Steps

#### Option 1: Virtual Environment (Recommended)

```bash
# Navigate to project directory
cd sql-data-lake-builder

# Create virtual environment
python3 -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test installation
python cli.py --help
```

#### Option 2: System-wide Installation

```bash
pip install -r requirements.txt
python cli.py --help
```

#### Option 3: Install as Package

```bash
pip install -e .
sql-data-lake-builder --help
```

### Verify Installation

```bash
python cli.py analyze --html examples/sample_mlb_data.html
```

Expected output:
```
🔍 Analyzing HTML file...
🏆 Sport: MLB
📊 Found 2 tables
```

---

## Docker Deployment

### Build Docker Image

```bash
# Create Dockerfile if not exists
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "cli.py"]
EOF

# Build image
docker build -t sql-datalake-builder:latest .
```

### Run in Docker

```bash
# Analyze HTML
docker run --rm -v $(pwd):/work sql-datalake-builder:latest \
  analyze --html /work/examples/sample_mlb_data.html

# Extract data
docker run --rm -v $(pwd):/work sql-datalake-builder:latest \
  extract --html /work/examples/sample_mlb_data.html \
  --output-dir /work/output

# Full pipeline
docker run --rm -v $(pwd):/work sql-datalake-builder:latest \
  full-pipeline --html /work/examples/sample_mlb_data.html
```

### Using Docker Compose

```yaml
version: '3.8'

services:
  extractor:
    build: .
    image: sql-datalake-builder:latest
    volumes:
      - ./html_files:/html
      - ./output:/app/output
    working_dir: /app
    command: full-pipeline --html /html/sports_data.html

  database:
    image: postgres:15
    environment:
      POSTGRES_DB: sports_datalake
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

Run with compose:
```bash
docker-compose up
```

---

## Production Deployment

### Cloud Deployment (AWS EC2)

```bash
#!/bin/bash
# deploy.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3-pip python3-venv postgresql

# Clone repository
git clone https://github.com/your-org/sql-datalake-builder.git
cd sql-datalake-builder

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/datalake-extractor.service > /dev/null << EOF
[Unit]
Description=SQL Data Lake Builder
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sql-datalake-builder
ExecStart=/home/ubuntu/sql-datalake-builder/venv/bin/python cli.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable datalake-extractor
sudo systemctl start datalake-extractor
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sql-datalake-builder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: datalake-extractor
  template:
    metadata:
      labels:
        app: datalake-extractor
    spec:
      containers:
      - name: extractor
        image: sql-datalake-builder:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: html-files
          mountPath: /html
        - name: output
          mountPath: /app/output
      volumes:
      - name: html-files
        persistentVolumeClaim:
          claimName: html-pvc
      - name: output
        persistentVolumeClaim:
          claimName: output-pvc
```

---

## Database Integration

### PostgreSQL Setup

```sql
-- Create database
CREATE DATABASE sports_datalake;

-- Create schema
CREATE SCHEMA IF NOT EXISTS datalake;

-- Create metadata table
CREATE TABLE datalake.extraction_log (
    id SERIAL PRIMARY KEY,
    source_url TEXT,
    sport VARCHAR(50),
    table_name VARCHAR(255),
    row_count INTEGER,
    extracted_at TIMESTAMP DEFAULT NOW(),
    extraction_time_ms INTEGER
);

-- Create indexed view for easy querying
CREATE VIEW datalake.latest_extractions AS
SELECT DISTINCT ON (sport, table_name) *
FROM datalake.extraction_log
ORDER BY sport, table_name, extracted_at DESC;
```

### Import Extracted Data to PostgreSQL

```python
import psycopg2
import pandas as pd

def import_to_postgres(json_file, table_name):
    """Import JSON data to PostgreSQL."""
    
    # Read JSON
    df = pd.read_json(json_file)
    
    # Connect to database
    conn = psycopg2.connect(
        dbname="sports_datalake",
        user="admin",
        password="password",
        host="localhost"
    )
    
    # Write to database
    from sqlalchemy import create_engine
    engine = create_engine('postgresql://admin:password@localhost/sports_datalake')
    df.to_sql(table_name, engine, schema='datalake', if_exists='append')
    
    conn.close()
    print(f"✅ Imported {len(df)} rows to {table_name}")

# Usage
import_to_postgres('output/team_rbis.json', 'mlb_rbis')
```

### MySQL Setup

```sql
CREATE DATABASE sports_datalake;
CREATE TABLE extraction_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_url VARCHAR(500),
    sport VARCHAR(50),
    table_name VARCHAR(255),
    row_count INT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Scheduling

### Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add extraction job (run daily at 2 AM)
0 2 * * * cd /home/user/sql-datalake-builder && \
  source venv/bin/activate && \
  python cli.py full-pipeline --html /data/sports.html >> /var/log/extraction.log 2>&1

# Run every Monday at 10 AM
0 10 * * 1 /home/user/sql-datalake-builder/run_extraction.sh

# Run every hour
0 * * * * cd /home/user/sql-datalake-builder && python cli.py extract --html /data/daily.html
```

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Data Lake Extraction"
4. Trigger: Daily at 2:00 AM
5. Action:
   - Program: `python.exe`
   - Arguments: `C:\path\to\cli.py full-pipeline --html C:\data\sports.html`
   - Start in: `C:\path\to\sql-datalake-builder`

### Python Scheduler (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from teamrankings_extractor import TeamRankingsExtractor

def scheduled_extraction():
    """Run extraction job."""
    extractor = TeamRankingsExtractor()
    tables = extractor.extract_from_html_file('data/sports.html')
    results = extractor.batch_export('./output', ['json', 'excel'])
    print(f"✅ Extracted {len(tables)} tables")

# Setup scheduler
scheduler = BackgroundScheduler()

# Daily at 2 AM
scheduler.add_job(
    scheduled_extraction,
    CronTrigger(hour=2, minute=0)
)

# Start scheduler
scheduler.start()

print("Scheduler started. Press Ctrl+C to exit.")
try:
    # Keep the scheduler running
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.shutdown()
```

---

## Monitoring

### Logging Configuration

```python
# config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file='extraction.log', log_level=logging.INFO):
    """Setup logging."""
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # File handler
    fh = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    
    # Console handler
    ch = logging.StreamHandler()
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

# Usage
logger = setup_logging('logs/extraction.log')
logger.info("Extraction started")
```

### Monitoring Dashboard

```python
# dashboard.py - Simple monitoring endpoint
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/status')
def status():
    """Get extraction status."""
    conn = psycopg2.connect("dbname=sports_datalake user=admin")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_extractions,
            COUNT(DISTINCT sport) as sports_count,
            SUM(row_count) as total_rows,
            MAX(extracted_at) as last_extraction
        FROM extraction_log
    """)
    
    result = cur.fetchone()
    conn.close()
    
    return jsonify({
        'total_extractions': result[0],
        'sports_count': result[1],
        'total_rows': result[2],
        'last_extraction': result[3].isoformat() if result[3] else None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Health Checks

```bash
#!/bin/bash
# health_check.sh

# Check if extraction is running
if ! pgrep -f "python cli.py" > /dev/null; then
    echo "❌ Extraction process not running"
    exit 1
fi

# Check database connection
python3 << EOF
import psycopg2
try:
    conn = psycopg2.connect("dbname=sports_datalake user=admin")
    conn.close()
    print("✅ Database healthy")
except Exception as e:
    print(f"❌ Database error: {e}")
    exit(1)
EOF

# Check output directory
if [ ! -d "./output" ] || [ -z "$(ls -A ./output)" ]; then
    echo "⚠️  Output directory empty"
    exit 1
fi

echo "✅ All health checks passed"
```

---

## Performance Optimization

### Parallel Extraction

```python
from concurrent.futures import ThreadPoolExecutor
import os

def parallel_extract(html_files, num_workers=4):
    """Extract multiple files in parallel."""
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        
        for html_file in html_files:
            future = executor.submit(extract_file, html_file)
            futures.append(future)
        
        for future in futures:
            results.append(future.result())
    
    return results

def extract_file(html_file):
    from teamrankings_extractor import TeamRankingsExtractor
    extractor = TeamRankingsExtractor()
    return extractor.extract_from_html_file(html_file)

# Usage
html_files = ['mlb.html', 'nfl.html', 'nba.html', 'wnba.html']
results = parallel_extract(html_files, num_workers=4)
```

---

## Troubleshooting

### Common Issues

**Issue: "No module named beautifulsoup4"**
```bash
pip install beautifulsoup4 lxml
```

**Issue: "Permission denied" on output**
```bash
chmod 755 ./output
```

**Issue: Database connection failed**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U admin -d sports_datalake -c "SELECT 1"
```

**Issue: Memory exceeded**
```python
# Process in chunks
import gc
extractor.batch_size = 50  # Smaller batches
gc.collect()  # Force garbage collection
```

---

## Next Steps

1. Set up monitoring dashboard
2. Configure automated backups
3. Implement data retention policies
4. Set up alerting for failures
5. Create runbooks for common issues

For more help, see the main [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).
