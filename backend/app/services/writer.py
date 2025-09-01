from __future__ import annotations
from typing import List, Tuple
from pathlib import Path
import json

from app.schemas.run import CurrentRun, Meta, Route, Frame, ENU, EKFState

def write_current_run(
    out_path: Path,
    source: str,
    dt: float,
    distance_km: float,
    eta_min_optimum: float,
    eta_min_vehicle: float,
    poly_lla: List[Tuple[float, float, float]],
    speed_limit_mps: List[float],
    vehicle_speed: List[float],
    v_opt: List[float],
    headings: List[float],
    enu_points: List[Tuple[float, float, float]],
    accel_body: List[Tuple[float, float, float]],
    ekf_series: List[Tuple[float, float, float, float, float]] | None = None,
):
    frames: List[Frame] = []
    t = 0.0
    for i, (lat, lon, alt) in enumerate(poly_lla):
        enu = enu_points[i]
        if ekf_series is not None and i < len(ekf_series):
            x, y, vx, vy, yaw_deg = ekf_series[i]
            ekf = EKFState(x_m=x, y_m=y, vx_mps=vx, vy_mps=vy, yaw_deg=yaw_deg)
        else:
            ekf = EKFState(x_m=enu[0], y_m=enu[1], vx_mps=0.0, vy_mps=0.0, yaw_deg=headings[i])
        frames.append(Frame(
            t=t,
            lat=lat,
            lon=lon,
            alt_m=alt,
            enu_m=ENU(x=enu[0], y=enu[1], z=enu[2]),
            heading_deg=headings[i],
            pitch_deg=0.0,
            roll_deg=0.0,
            vehicle_speed_mps=vehicle_speed[i],
            optimum_speed_mps=v_opt[i],
            accel_body_mps2=list(accel_body[i]),
            gyro_body_rps=[0.0, 0.0, 0.0],
            ekf=ekf,
        ))
        t += dt
    doc = CurrentRun(
        meta=Meta(
            source=source,
            dt=dt,
            distance_km=distance_km,
            eta_min_optimum=eta_min_optimum,
            eta_min_vehicle=eta_min_vehicle,
        ),
        route=Route(
            polyline=[(lat, lon, alt) for (lat, lon, alt) in poly_lla],
            speed_limit_mps=speed_limit_mps if len(speed_limit_mps) == len(poly_lla) else speed_limit_mps[: len(poly_lla)],
        ),
        frames=frames,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc.model_dump_json(indent=2))
    return doc