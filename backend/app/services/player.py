from __future__ import annotations
from typing import List, Tuple
import math

from app.utils.geo import lla_to_enu_series

A_DRIVE = 1.8  # m/s² accel limit  
A_BRAKE = 3.5  # m/s² brake limit

def simulate_vehicle(poly_lla: List[Tuple[float, float, float]], v_opt: List[float], dt: float):
    n = len(poly_lla)
    enu_points, _ = lla_to_enu_series(poly_lla)
    vehicle_speed = [0.0] * n
    accel_body = [(0.0, 0.0, 9.81)] * n
    heading_deg = [0.0] * n

    for i in range(1, n):
        target = v_opt[i]
        v_prev = vehicle_speed[i - 1]
        if target > v_prev:
            v_new = min(target, v_prev + A_DRIVE * dt)
        else:
            v_new = max(target, v_prev - A_BRAKE * dt)
        vehicle_speed[i] = v_new

        dx = enu_points[i][0] - enu_points[i - 1][0]
        dy = enu_points[i][1] - enu_points[i - 1][1]
        heading_deg[i] = math.degrees(math.atan2(dx, dy))

        ax = (v_new - v_prev) / dt
        accel_body[i] = (ax, 0.0, 9.81)

    return vehicle_speed, accel_body, heading_deg, enu_points