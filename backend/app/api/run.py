from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
from pathlib import Path
import json

from app.schemas.run import CurrentRun
from app.services.planner import plan_speed_profile
from app.services.player import simulate_vehicle
from app.services.imu import generate_imu
from app.services.writer import write_current_run

router = APIRouter(prefix="/api/run", tags=["run"])

class PolylineRunRequest(BaseModel):
    polyline: List[Tuple[float, float]]
    speed_limit_mps: List[float]
    dt: float = 0.1

@router.post("/polyline", response_model=CurrentRun)
async def run_with_polyline(req: PolylineRunRequest):
    if len(req.polyline) < 2:
        raise HTTPException(400, "Polyline too short")
    if not req.speed_limit_mps:
        raise HTTPException(400, "Missing speed limits")

    v_opt, distance_km, eta_min_opt = plan_speed_profile(req.polyline, req.speed_limit_mps, req.dt)
    poly_lla = [(lat, lon, 0.0) for (lat, lon) in req.polyline]
    vehicle_speed, accel_body, heading_deg, enu_points = simulate_vehicle(poly_lla, v_opt, req.dt)
    gyro_body = generate_imu(accel_body, heading_deg, req.dt)

    total_s = 0.0
    from app.utils.geo import polyline_length_m
    for i in range(len(req.polyline) - 1):
        ds = polyline_length_m([req.polyline[i], req.polyline[i + 1]])
        v_seg = max((vehicle_speed[i] + vehicle_speed[i + 1]) * 0.5, 0.1)
        total_s += ds / v_seg
    eta_min_vehicle = total_s / 60.0

    out_path = Path("simulator/current_run.json")
    doc = write_current_run(
        out_path=out_path,
        source="HERE+ElevationStub",
        dt=req.dt,
        distance_km=distance_km,
        eta_min_optimum=eta_min_opt,
        eta_min_vehicle=eta_min_vehicle,
        poly_lla=poly_lla,
        speed_limit_mps=req.speed_limit_mps,
        vehicle_speed=vehicle_speed,
        v_opt=v_opt,
        headings=heading_deg,
        enu_points=enu_points,
        accel_body=accel_body,
        ekf_series=None,
    )
    data = doc.model_dump()
    for i in range(min(len(data["frames"]), len(gyro_body))):
        data["frames"][i]["gyro_body_rps"] = list(gyro_body[i])
    out_path.write_text(json.dumps(data, indent=2))