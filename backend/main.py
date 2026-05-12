"""
Dam Analysis System - FastAPI Backend
Handles file uploads, analysis orchestration, and results delivery
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import uuid
import os
import shutil
import asyncio
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Dam Analysis System", version="1.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
SCRIPTS_DIR = BASE_DIR.parent / "scripts"

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory task storage (in production, use Redis)
tasks = {}

class AnalysisCriteria(BaseModel):
    min_order: int = 3
    max_order: int = 5
    min_drainage: float = 50.0
    max_drainage: float = 5000.0
    min_volume: float = 5.0
    max_dam_length: float = 1000.0
    max_slope: float = 35.0
    search_interval: float = 500.0

class TaskStatus(BaseModel):
    task_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: int
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {
        "app": "Dam Analysis System",
        "version": "1.0",
        "status": "running",
        "endpoints": [
            "/api/analyze",
            "/api/status/{task_id}",
            "/api/download/{task_id}/{filename}",
            "/api/health"
        ]
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/analyze")
async def analyze_basin(
    background_tasks: BackgroundTasks,
    dem: UploadFile = File(...),
    rivers: UploadFile = File(...),
    boundary: UploadFile = File(...),
    criteria: str = Form(...)
):
    """
    Start basin analysis
    Files are uploaded and processed in background
    """
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Parse criteria
    try:
        criteria_dict = json.loads(criteria)
        criteria_obj = AnalysisCriteria(**criteria_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid criteria: {str(e)}")
    
    # Create task directory
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(exist_ok=True)
    
    # Save uploaded files
    try:
        dem_path = task_dir / "dem.tif"
        rivers_path = task_dir / "rivers.shp"
        boundary_path = task_dir / "boundary.shp"
        
        # Save DEM
        with open(dem_path, "wb") as f:
            shutil.copyfileobj(dem.file, f)
        
        # Save rivers (handle zip or shp)
        if rivers.filename.endswith('.zip'):
            rivers_zip = task_dir / "rivers.zip"
            with open(rivers_zip, "wb") as f:
                shutil.copyfileobj(rivers.file, f)
            # Extract
            shutil.unpack_archive(rivers_zip, task_dir / "rivers")
        else:
            with open(rivers_path, "wb") as f:
                shutil.copyfileobj(rivers.file, f)
        
        # Save boundary
        if boundary.filename.endswith('.zip'):
            boundary_zip = task_dir / "boundary.zip"
            with open(boundary_zip, "wb") as f:
                shutil.copyfileobj(boundary.file, f)
            shutil.unpack_archive(boundary_zip, task_dir / "boundary")
        else:
            with open(boundary_path, "wb") as f:
                shutil.copyfileobj(boundary.file, f)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    
    # Initialize task status
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "criteria": criteria_dict
    }
    
    # Start background task
    background_tasks.add_task(
        run_analysis,
        task_id,
        task_dir,
        criteria_obj
    )
    
    return {"task_id": task_id, "status": "pending"}

async def run_analysis(task_id: str, task_dir: Path, criteria: AnalysisCriteria):
    """
    Run the analysis pipeline in background
    """
    import subprocess
    import sys
    
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 10
        tasks[task_id]["message"] = "데이터 검증 중..."
        
        # Create config file
        config = {
            "river_filters": {
                "min_order": criteria.min_order,
                "max_order": criteria.max_order,
                "min_drainage_area_m2": criteria.min_drainage * 1e6,
                "max_drainage_area_m2": criteria.max_drainage * 1e6
            },
            "dam_criteria": {
                "min_volume_mm3": criteria.min_volume,
                "max_dam_length": criteria.max_dam_length,
                "height_min": 40,
                "height_max": 120,
                "height_step": 10
            },
            "terrain_criteria": {
                "max_slope_degree": criteria.max_slope
            },
            "spatial_criteria": {
                "search_interval": criteria.search_interval,
                "min_distance_between_sites": 2000
            },
            "paths": {
                "dem": str(task_dir / "dem.tif"),
                "rivers": str(task_dir / "rivers"),
                "boundary": str(task_dir / "boundary"),
                "output_dir": str(OUTPUT_DIR / task_id)
            }
        }
        
        config_path = task_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create output directory
        output_dir = OUTPUT_DIR / task_id
        output_dir.mkdir(exist_ok=True)
        
        # Step 1: Site selection
        tasks[task_id]["progress"] = 20
        tasks[task_id]["message"] = "댐 적지 선정 중..."
        
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "01_site_selection.py"), str(config_path)],
            capture_output=True,
            text=True,
            cwd=str(task_dir)
        )
        
        if result.returncode != 0:
            raise Exception(f"Site selection failed: {result.stderr}")
        
        # Step 2: Generate profiles
        tasks[task_id]["progress"] = 50
        tasks[task_id]["message"] = "프로파일 생성 중..."
        
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "02_generate_profiles.py"), str(config_path)],
            capture_output=True,
            text=True,
            cwd=str(task_dir)
        )
        
        if result.returncode != 0:
            raise Exception(f"Profile generation failed: {result.stderr}")
        
        # Step 3: Generate flood polygons and dam lengths
        tasks[task_id]["progress"] = 80
        tasks[task_id]["message"] = "침수 영역 및 댐 길이 계산 중..."
        
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "03_generate_flood_damlengths.py"), str(config_path)],
            capture_output=True,
            text=True,
            cwd=str(task_dir)
        )
        
        if result.returncode != 0:
            raise Exception(f"Flood/dam length generation failed: {result.stderr}")
        
        # Load results summary
        candidates_path = output_dir / "candidates.js"
        if candidates_path.exists():
            # Parse candidates count and summary
            with open(candidates_path, 'r') as f:
                content = f.read()
                # Simple count (in production, parse properly)
                num_sites = content.count('"id"')
            
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "분석 완료!"
            tasks[task_id]["result"] = {
                "total_sites": num_sites,
                "files": [
                    "candidates.js",
                    "profiles.js",
                    "floodPolygons.js",
                    "damLengths.js"
                ],
                "summary": f"{num_sites}개 후보지 발견"
            }
        else:
            raise Exception("Results file not found")
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["progress"] = 0
        tasks[task_id]["message"] = "분석 실패"
        tasks[task_id]["error"] = str(e)

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get analysis task status
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]

@app.get("/api/download/{task_id}/{filename}")
async def download_result(task_id: str, filename: str):
    """
    Download result file
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed")
    
    file_path = OUTPUT_DIR / task_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/javascript"
    )

@app.get("/api/results/{task_id}")
async def get_results_summary(task_id: str):
    """
    Get analysis results summary (for display)
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed")
    
    # Load and parse results
    try:
        geojson_path = OUTPUT_DIR / task_id / "dam_sites.geojson"
        with open(geojson_path, 'r') as f:
            geojson = json.load(f)
        
        sites = []
        for feature in geojson['features']:
            props = feature['properties']
            coords = feature['geometry']['coordinates']
            sites.append({
                'id': props['id'],
                'lat': coords[1],
                'lon': coords[0],
                'volume': props['volume_mm3'],
                'height': props['height_m'],
                'damLength': props['dam_length_m'],
                'bed': props['bed_elev'],
                'order': props['stream_order']
            })
        
        return {
            "task_id": task_id,
            "total_sites": len(sites),
            "sites": sites,
            "files": tasks[task_id]["result"]["files"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load results: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
