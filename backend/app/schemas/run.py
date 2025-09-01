from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
from datetime import datetime

LatLonAlt = Tuple[float, float, float]

class RunRequest(BaseModel):
    start: Tuple[float, float]  # (lat, lon)
    end: Tuple[float, float]    # (lat, lon)
    dt: float = Field(0.1, gt=0)
    traffic: bool = False
    max_km: float = 150.0

class Meta(BaseModel):
    source: str
    dt: float
    units: str = "SI"
    distance_km: float
    eta_min_optimum: float
    eta_min_vehicle: float
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class Route(BaseModel):
    polyline: List[LatLonAlt]  # [ [lat, lon, alt_m], ... ] (alt_m can be 0 now)
    speed_limit_mps: List[float]  # same length as polyline or len-1 per segment (we accept both)

class ENU(BaseModel):
    x: float
    y: float
    z: float

class EKFState(BaseModel):
    x_m: float
    y_m: float
    vx_mps: float
    vy_mps: float
    yaw_deg: float

class Frame(BaseModel):
    t: float
    lat: float
    lon: float
    alt_m: float
    enu_m: ENU
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    vehicle_speed_mps: float
    optimum_speed_mps: float
    accel_body_mps2: List[float]  # [ax, ay, az]
    gyro_body_rps: List[float]    # [gx, gy, gz]
    ekf: EKFState

class CurrentRun(BaseModel):
    meta: Meta
    route: Route
    frames: List[Frame]