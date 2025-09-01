from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_snap import router as snap_router
from app.api.routes_route import router as route_router
from app.api.routes_files import router as files_router
from app.core.logger import get_logger
from app.core.config import HERE_API_KEY, ORS_API_KEY
from pathlib import Path

logger = get_logger(__name__)

app = FastAPI(title="SmartAutoBus", version="modular-1.0")

# CORS configuration for production
origins = [
    "http://localhost:3000",  # Development
    "https://localhost:3000", # Development HTTPS
    "https://speedsimulator.tech",  # Production domain
    "https://www.speedsimulator.tech",  # Production www
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(snap_router)
app.include_router(route_router)
app.include_router(files_router)

@app.get("/")
async def root():
    return {"message": "SmartAutoBus API running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

@app.on_event("startup")
async def startup():
    sim_dir = Path(__file__).resolve().parent.parent / "simulator"
    logger.info("============================================")
    logger.info("🚍 SmartAutoBus API Starting")
    logger.info("HERE key: %s", "YES" if HERE_API_KEY else "NO")
    logger.info("ORS  key: %s", "YES" if ORS_API_KEY  else "NO")
    logger.info("SIM dir: %s", sim_dir)
    logger.info("============================================")
