# Installing SQL Data Lake Builder into CRANE V1

## Summary

This guide shows how to integrate the **SQL Data Lake Builder** into the existing **CRANE V1** project.

The tool will add sports data extraction capabilities to CRANE's backend.

---

## Step 1: Copy Tool into CRANE Project

```bash
# Navigate to CRANE
cd /home/hunt/crane

# Copy the SQL Data Lake Builder
cp -r /home/hunt/Downloads/FOR\ SQL/sql-data-lake-builder ./sports-datalake

# Verify copy
ls -la sports-datalake/
```

Expected output:
```
drwxrwxr-x  src/
drwxrwxr-x  examples/
-rw-r--r--  cli.py
-rw-r--r--  models_config.py
-rw-r--r--  crane_integration.py
-rw-r--r--  requirements.txt
-rw-r--r--  README.md
-rw-r--r--  QUICKSTART.md
-rw-r--r--  DEPLOYMENT.md
```

---

## Step 2: Install Dependencies

```bash
# Navigate to sports-datalake
cd /home/hunt/crane/sports-datalake

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Additionally install FastAPI for REST API
pip install fastapi uvicorn

# Verify installation
python3 cli.py --help
```

Expected output:
```
Usage: cli.py [OPTIONS] COMMAND [ARGS]...
  SQL Data Lake Builder - Extract sports data and generate schemas.

Commands:
  analyze           Analyze HTML file...
  extract           Extract tables...
  full-pipeline     Complete extraction pipeline...
```

---

## Step 3: Add to CRANE Backend

Edit `/home/hunt/crane/backend/src/main.rs` to add sports data extraction endpoint:

```rust
// Add this module after other imports
mod sports_datalake {
    use std::process::Command;
    
    pub async fn extract_sports_data(html_path: String) -> Result<String, String> {
        let output = Command::new("python3")
            .arg("sports-datalake/cli.py")
            .arg("full-pipeline")
            .arg("--html")
            .arg(&html_path)
            .current_dir("/home/hunt/crane")
            .output()
            .map_err(|e| format!("Failed to run extractor: {}", e))?;
        
        let result = String::from_utf8_lossy(&output.stdout);
        Ok(result.to_string())
    }
}

// Add this route in the router setup
pub fn add_sports_routes(app: Router) -> Router {
    app.route("/api/sports/extract", post(extract_sports_handler))
}

// Handler function
async fn extract_sports_handler(body: UploadFile) -> Json<serde_json::Value> {
    // Call sports_datalake::extract_sports_data()
    // Return JSON result
}
```

---

## Step 4: Verify Integration

Test that everything works together:

```bash
# From CRANE root
cd /home/hunt/crane

# Test extraction directly
python3 sports-datalake/cli.py analyze --html sports-datalake/examples/sample_mlb_data.html

# Expected output:
# 🔍 Analyzing HTML file...
# 🏆 Sport: MLB
# 📊 Found 2 tables
```

---

## Step 5: Wire React Frontend (Optional)

Create a new sports data extraction component in CRANE frontend:

**File**: `/home/hunt/crane/src-tauri/frontend/src/SportsExtractor.jsx`

```jsx
import React, { useState } from 'react';

export default function SportsExtractor() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleExtract = async () => {
    if (!file) return;
    
    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8002/api/sports/extract', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Extraction failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>🏆 Sports Data Extractor</h2>
      
      <input
        type="file"
        accept=".html"
        onChange={(e) => setFile(e.target.files[0])}
      />
      
      <button
        onClick={handleExtract}
        disabled={!file || loading}
      >
        {loading ? 'Extracting...' : 'Extract Data'}
      </button>
      
      {results && (
        <div>
          <h3>Results</h3>
          <pre>{JSON.stringify(results, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
```

---

## Step 6: Start Services

```bash
# Terminal 1: Start CRANE backend
cd /home/hunt/crane
cargo run --release

# Terminal 2: Start REST API for sports data
cd /home/hunt/crane/sports-datalake
source venv/bin/activate
python3 crane_integration.py

# Terminal 3: (Optional) Start CRANE frontend
cd /home/hunt/crane/src-tauri
npm start
```

---

## Verification Checklist

- [ ] Files copied to CRANE project
- [ ] Dependencies installed
- [ ] `cli.py --help` works
- [ ] Example extraction works
- [ ] Backend compiles without errors
- [ ] REST API starts on port 8003
- [ ] Frontend component added
- [ ] Services started successfully

---

## Usage in CRANE

Once integrated, you can:

1. **From CLI**:
```bash
cd /home/hunt/crane/sports-datalake
python3 cli.py full-pipeline --html /path/to/sports_data.html
```

2. **From Python Code**:
```python
from sports_datalake.src.teamrankings_extractor import TeamRankingsExtractor

extractor = TeamRankingsExtractor()
tables = extractor.extract_from_html_file('sports_data.html')
```

3. **From API**:
```bash
curl -X POST http://localhost:8003/extract/upload \
  -F "file=@sports_data.html"
```

---

## Troubleshooting

**Problem**: `ModuleNotFoundError: No module named 'beautifulsoup4'`
```bash
cd sports-datalake
source venv/bin/activate
pip install beautifulsoup4 lxml pandas click openpyxl
```

**Problem**: Port 8003 already in use
```bash
# Edit crane_integration.py, line 325:
uvicorn.run(app, host="0.0.0.0", port=8004)  # Change 8003 to 8004
```

**Problem**: Extraction returns empty
```bash
# Verify HTML file has tables
python3 cli.py analyze --html /path/to/file.html
```

---

## Next Steps

1. ✅ Copy & install tool into CRANE
2. ✅ Verify CLI works
3. ✅ Add backend endpoint
4. ✅ Wire frontend component
5. Add React Flow visualization for pipeline
6. Integrate TimesFM prediction model
7. Integrate DeepSeek Math model
8. Add live monitoring dashboard

---

## Support

For issues or questions:
- Check `VERIFICATION_REPORT.md` for test results
- Review `QUICKSTART.md` for basic usage
- See `README.md` for full documentation

---

**Ready to integrate? Start with Step 1!** 🚀
