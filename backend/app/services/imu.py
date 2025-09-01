from __future__ import annotations
from typing import List, Tuple
import math

def generate_imu(accel_body: List[Tuple[float, float, float]], heading_deg: List[float], dt: float):
    n = len(accel_body)
    gyro_body = [(0.0, 0.0, 0.0)] * n
    for i in range(1, n):
        dyaw = heading_deg[i] - heading_deg[i - 1]
        if dyaw > 180:
            dyaw -= 360
        elif dyaw < -180:
            dyaw += 360
        gyro_body[i] = (0.0, 0.0, math.radians(dyaw) / dt)
    return gyro_body