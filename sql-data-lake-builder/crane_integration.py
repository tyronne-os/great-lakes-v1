"""
CRANE V1 Integration Module

Integrates SQL Data Lake Builder with CRANE IDE backend.
Provides REST API endpoints for sports data extraction and prediction.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from teamrankings_extractor import TeamRankingsExtractor
from json_formatter import JSONFormatter
from models_config import TimesFMPredictor, DeepSeekMathReasoner

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI
app = FastAPI(
    title="Sports Data Lake API",
    description="Extract sports data and generate predictions",
    version="1.0.0"
)

# CORS middleware for CRANE frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class DataLakeState:
    def __init__(self):
        self.extractor: Optional[TeamRankingsExtractor] = None
        self.formatter = JSONFormatter()
        self.timesfm: Optional[TimesFMPredictor] = None
        self.deepseek: Optional[DeepSeekMathReasoner] = None
        self.last_extraction = None
        self.output_dir = Path("./lake_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

state = DataLakeState()


# ===== Health & Status Endpoints =====

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "sports-data-lake",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/status")
async def status():
    """Get current data lake status."""
    return {
        "extractor_ready": state.extractor is not None,
        "models_loaded": {
            "timesfm": state.timesfm is not None,
            "deepseek": state.deepseek is not None,
        },
        "last_extraction": state.last_extraction,
        "output_directory": str(state.output_dir),
        "output_files": len(list(state.output_dir.glob("*"))),
    }


# ===== Extraction Endpoints =====

@app.post("/extract/upload")
async def extract_from_upload(
    file: UploadFile = File(...),
    sport: Optional[str] = None
):
    """
    Extract data from uploaded HTML file.
    
    Args:
        file: HTML file to extract
        sport: Sport type (auto-detected if None)
    
    Returns:
        Extraction results
    """
    try:
        # Save uploaded file
        upload_path = state.output_dir / f"upload_{datetime.now().timestamp()}.html"
        contents = await file.read()
        upload_path.write_bytes(contents)
        
        # Extract
        extractor = TeamRankingsExtractor(sport=sport or 'mlb')
        tables = extractor.extract_from_html_file(str(upload_path))
        
        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in HTML")
        
        # Auto-detect sport
        with open(upload_path) as f:
            html_content = f.read()
        detected_sport = extractor.detect_sport_type(html_content)
        
        # Store extractor state
        state.extractor = extractor
        state.last_extraction = {
            "timestamp": datetime.now().isoformat(),
            "sport": detected_sport,
            "tables_found": len(tables),
            "source_file": str(upload_path),
        }
        
        # Get summary
        summary = extractor.get_summary()
        
        return {
            "status": "success",
            "extraction": {
                "sport_detected": detected_sport,
                "tables_found": len(tables),
                "summary": summary,
                "tables": [
                    {
                        "id": t["table_id"],
                        "title": t["title"],
                        "rows": t["row_count"],
                        "columns": t["col_count"],
                        "confidence": t["confidence"],
                    }
                    for t in tables[:10]  # Limit to first 10
                ]
            }
        }
    
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extract/analyze")
async def analyze_extraction():
    """Get details about last extraction."""
    if not state.extractor or not state.extractor.extracted_data:
        raise HTTPException(status_code=400, detail="No extraction data available")
    
    summary = state.extractor.get_summary()
    return {
        "status": "success",
        "analysis": {
            "total_tables": summary["total_tables"],
            "sports_tables": summary["sports_tables"],
            "total_rows": summary["total_rows"],
            "high_confidence": summary["high_confidence"],
            "tables": summary["tables"],
        }
    }


# ===== Export Endpoints =====

@app.post("/export/json")
async def export_json(table_id: int = 0):
    """Export extracted data as JSON."""
    if not state.extractor or not state.extractor.extracted_data:
        raise HTTPException(status_code=400, detail="No extraction data available")
    
    try:
        tables = state.extractor.extracted_data
        if table_id >= len(tables):
            raise HTTPException(status_code=400, detail=f"Table {table_id} not found")
        
        table = tables[table_id]
        json_str = state.extractor.to_json(table)
        
        output_file = state.output_dir / f"export_{table_id}_{datetime.now().timestamp()}.json"
        output_file.write_text(json_str)
        
        return JSONResponse(content=json.loads(json_str))
    
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/excel")
async def export_excel(table_id: int = 0):
    """Export extracted data as Excel."""
    if not state.extractor or not state.extractor.extracted_data:
        raise HTTPException(status_code=400, detail="No extraction data available")
    
    try:
        tables = state.extractor.extracted_data
        if table_id >= len(tables):
            raise HTTPException(status_code=400, detail=f"Table {table_id} not found")
        
        table = tables[table_id]
        output_file = state.output_dir / f"export_{table_id}_{datetime.now().timestamp()}.xlsx"
        
        state.extractor.to_excel(table, str(output_file))
        
        return FileResponse(
            path=output_file,
            filename=output_file.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/all")
async def export_all(formats: Optional[str] = "json,excel,csv"):
    """Export all extracted data in multiple formats."""
    if not state.extractor or not state.extractor.extracted_data:
        raise HTTPException(status_code=400, detail="No extraction data available")
    
    try:
        export_formats = formats.split(",")
        results = state.extractor.batch_export(str(state.output_dir), export_formats)
        
        return {
            "status": "success",
            "exports": {
                fmt: len(files) for fmt, files in results.items()
            },
            "output_directory": str(state.output_dir),
        }
    
    except Exception as e:
        logger.error(f"Batch export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Prediction Endpoints =====

@app.post("/predict/timeseries")
async def predict_timeseries(
    data: Dict[str, Any],
    steps: int = 10
):
    """
    Forecast time series data using TimesFM.
    
    Args:
        data: { "team": "name", "stat": "PPG", "values": [1.0, 2.0, ...] }
        steps: Number of steps to forecast
    
    Returns:
        Forecast results
    """
    try:
        if not state.timesfm:
            state.timesfm = TimesFMPredictor()
            state.timesfm.load_model()
        
        if not state.timesfm.model:
            raise HTTPException(status_code=500, detail="TimesFM model not loaded")
        
        forecast_result = state.timesfm.forecast(
            data.get("values", []),
            steps
        )
        
        return {
            "status": "success",
            "prediction": {
                "model": "TimesFM",
                "team": data.get("team", "Unknown"),
                "statistic": data.get("stat", "Unknown"),
                "historical_avg": sum(data["values"]) / len(data["values"]),
                "forecast": forecast_result,
            }
        }
    
    except Exception as e:
        logger.error(f"TimesFM prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/outcome")
async def predict_outcome(game_data: Dict[str, Any]):
    """
    Predict game outcome using DeepSeek Math reasoning.
    
    Args:
        game_data: {
            "team1": "name",
            "team2": "name",
            "team1_stats": { "ppg": 100, ... },
            "team2_stats": { "ppg": 95, ... }
        }
    
    Returns:
        Prediction with reasoning
    """
    try:
        if not state.deepseek:
            state.deepseek = DeepSeekMathReasoner()
            state.deepseek.load_model()
        
        if not state.deepseek.model:
            raise HTTPException(status_code=500, detail="DeepSeek model not loaded")
        
        prediction = state.deepseek.predict_game_outcome(game_data)
        
        return {
            "status": "success",
            "prediction": prediction
        }
    
    except Exception as e:
        logger.error(f"Outcome prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Model Management Endpoints =====

@app.post("/models/download")
async def download_models(background_tasks: BackgroundTasks):
    """Download prediction models from Hugging Face."""
    try:
        from models_config import setup_prediction_models
        
        def download_in_bg():
            logger.info("Starting model downloads...")
            models = setup_prediction_models()
            logger.info(f"Downloaded {len(models)} models")
        
        background_tasks.add_task(download_in_bg)
        
        return {
            "status": "downloading",
            "message": "Models downloading in background",
        }
    
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/status")
async def models_status():
    """Get status of downloaded models."""
    from models_config import ModelManager
    
    manager = ModelManager()
    
    return {
        "status": "success",
        "models": {
            "timesfm": {
                "loaded": state.timesfm is not None,
                "info": manager.get_model_info("timesfm"),
            },
            "deepseek_math": {
                "loaded": state.deepseek is not None,
                "info": manager.get_model_info("deepseek_math"),
            }
        }
    }


# ===== Output & Files Endpoints =====

@app.get("/files/list")
async def list_files():
    """List all generated files."""
    files = []
    for f in state.output_dir.glob("*"):
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
            })
    
    return {
        "status": "success",
        "files": files,
        "output_directory": str(state.output_dir),
    }


@app.get("/files/download/{filename}")
async def download_file(filename: str):
    """Download a generated file."""
    file_path = state.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Sports Data Lake API...")
    logger.info("Available at http://localhost:8003")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
