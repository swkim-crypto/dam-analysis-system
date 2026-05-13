#!/usr/bin/env python3
"""
Dam Site Analysis System - FastAPI Backend
"""

import os
import sys
import uuid
import json
import shutil
import asyncio
import subprocess
import yaml
from pathlib import Path
from typing import Optional
import aiofiles

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="Dam Site Analysis API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage
tasks = {}

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
SCRIPTS_DIR = Path("scripts")

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def make_config(task_dir: Path, criteria: dict) -> dict:
    """Generate config.yaml for analysis scripts"""
    config = {
        "paths": {
            "dem": str(task_dir / "dem.tif"),
            "rivers": str(task_dir / "rivers"),
            "boundary": str(task_dir / "boundary.shp"),
            "output_dir": str(task_dir / "output"),
        },
        "crs": {
            "working_crs": "EPSG:32648",
            "output_crs": "EPSG:4326",
        },
        "river_filters": {
            "min_order": criteria.get("min_order", 3),
            "max_order": criteria.get("max_order", 5),
            "min_drainage_area_m2": criteria.get("min_drainage", 50) * 1e6,
            "max_drainage_area_m2": criteria.get("max_drainage", 5000) * 1e6,
            "min_slope": 0.0,
            "max_slope": criteria.get("max_slope", 35) / 100,
        },
        "spatial_criteria": {
            "search_interval": criteria.get("search_interval", 500),
            "min_distance_between_sites": 2000,
        },
        "terrain_criteria": {
            "max_slope_deg": criteria.get("max_slope", 35),
        },
        "dam_criteria": {
            "height_min": 40,
            "height_max": 120,
            "height_step": 10,
            "min_volume_mm3": criteria.get("min_volume", 5.0),
            "max_dam_length": criteria.get("max_dam_length", 1000),
            "valley_narrowness_max": 20,
        },
        "output": {
            "export_geojson": True,
            "export_csv": True,
            "export_js": True,
        },
    }
    return config


async def run_analysis(task_id: str, task_dir: Path, criteria: dict):
    """Run 3 analysis scripts sequentially in background"""
    task = tasks[task_id]

    def update(progress, message):
        task["progress"] = progress
        task["message"] = message
        print(f"[{task_id[:8]}] {progress}% - {message}")

    try:
        # Write config.yaml into task directory
        config = make_config(task_dir, criteria)
        config_path = task_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        output_dir = task_dir / "output"
        output_dir.mkdir(exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent)

        def run_script(script_name, cwd):
            script_path = SCRIPTS_DIR / script_name
            result = subprocess.run(
                [sys.executable, str(script_path.resolve())],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                env=env,
            )
            return result

        # Step 1: Site selection
        update(10, "후보지 탐색 중...")
        result = run_script("01_site_selection.py", task_dir)
        if result.returncode != 0:
            raise RuntimeError(f"Site selection failed: {result.stderr}")
        update(35, "후보지 탐색 완료")

        # Step 2: Profiles
        update(40, "프로파일 생성 중...")
        result = run_script("02_generate_profiles.py", task_dir)
        if result.returncode != 0:
            raise RuntimeError(f"Profile generation failed: {result.stderr}")
        update(65, "프로파일 생성 완료")

        # Step 3: Flood polygons & dam lengths
        update(70, "침수 분석 중...")
        result = run_script("03_generate_flood_damlengths.py", task_dir)
        if result.returncode != 0:
            raise RuntimeError(f"Flood/damlength generation failed: {result.stderr}")
        update(95, "침수 분석 완료")

        # Collect results
        sites = []
        geojson_path = output_dir / "dam_sites.geojson"
        if geojson_path.exists():
            with open(geojson_path) as f:
                gj = json.load(f)
            for feat in gj["features"]:
                p = feat["properties"]
                c = feat["geometry"]["coordinates"]
                sites.append({
                    "id": p["id"],
                    "lat": c[1],
                    "lon": c[0],
                    "bed": p["bed_elev"],
                    "height": p.get("height_m"),
                    "volume": p.get("volume_mm3"),
                    "damLength": p.get("dam_length_m"),
                    "order": p.get("stream_order"),
                })

        # List downloadable files
        files = [f.name for f in output_dir.iterdir()
                 if f.suffix in (".js", ".geojson", ".csv")]

        task.update({
            "status": "completed",
            "progress": 100,
            "message": f"분석 완료 - {len(sites)}개 후보지 발견",
            "total_sites": len(sites),
            "sites": sites,
            "files": files,
        })

    except Exception as e:
        task.update({
            "status": "failed",
            "progress": task.get("progress", 0),
            "message": str(e),
        })


@app.get("/")
def root():
    return {"status": "ok", "service": "Dam Site Analysis API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/analyze")
async def analyze(
    dem: UploadFile = File(...),
    rivers: UploadFile = File(...),
    boundary: UploadFile = File(...),
    criteria: str = Form("{}"),
):
    task_id = str(uuid.uuid4())
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True)

    # Save uploaded files
    async def save(upload: UploadFile, dest: Path):
        async with aiofiles.open(dest, "wb") as f:
            content = await upload.read()
            await f.write(content)

    await save(dem, task_dir / "dem.tif")

    # Rivers: save to rivers/ subfolder (supports .shp or single file)
    rivers_dir = task_dir / "rivers"
    rivers_dir.mkdir()
    rivers_filename = rivers.filename or "rivers.shp"
    await save(rivers, rivers_dir / rivers_filename)

    await save(boundary, task_dir / "boundary.shp")

    try:
        criteria_dict = json.loads(criteria)
    except Exception:
        criteria_dict = {}

    tasks[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "message": "분석 준비 중...",
    }

    asyncio.create_task(run_analysis(task_id, task_dir, criteria_dict))

    return {"task_id": task_id, "status": "processing"}


@app.get("/api/status/{task_id}")
def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
    }


@app.get("/api/results/{task_id}")
def get_results(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed")
    return {
        "task_id": task_id,
        "total_sites": task.get("total_sites", 0),
        "sites": task.get("sites", []),
        "files": task.get("files", []),
    }


@app.get("/api/download/{task_id}/{filename}")
def download_file(task_id: str, filename: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    file_path = UPLOAD_DIR / task_id / "output" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
