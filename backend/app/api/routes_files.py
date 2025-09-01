from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.core.config import SIM_DIR

router = APIRouter()

@router.get("/api/files/route")
async def get_route():
    """Get the current route file."""
    route_file = SIM_DIR / "route.json"
    if not route_file.exists():
        raise HTTPException(404, "Route file not found")
    
    try:
        import json
        with open(route_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Error reading route file: {e}")

@router.get("/api/files/current-run")
async def get_current_run():
    """Get the current run data."""
    run_file = SIM_DIR / "current_run.json"
    if not run_file.exists():
        raise HTTPException(404, "Current run file not found")
    
    try:
        import json
        with open(run_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Error reading current run file: {e}")
