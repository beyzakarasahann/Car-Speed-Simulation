from __future__ import annotations
from typing import List, Tuple
import math

from app.utils.geo import curvature_series, polyline_length_m

# Comfort/dynamics defaults (tunable)
A_DRIVE = 1.8      # m/s^2
A_BRAKE = 3.5      # m/s^2 (positive value; we apply as decel)
JERK_MAX = 0.8     # m/s^3 (not enforced strictly; used to smooth accel targets)
A_LAT_MAX = 1.5    # m/s^2 lateral comfort cap


def _cap_by_curvature(vfree: List[float], poly_ll: List[Tuple[float, float]]) -> List[float]:
    """Cap speeds by lateral acceleration comfort using curvature κ.
    v_cap = min(vfree, sqrt(a_lat_max / κ)). κ=0 -> no cap."""
    kappa = curvature_series(poly_ll)
    out = []
    for v, k in zip(vfree, kappa):
        if k <= 1e-9:
            out.append(v)
        else:
            vmax_curve = math.sqrt(max(A_LAT_MAX / k, 0.0))
            out.append(min(v, vmax_curve))
    return out


def _forward_backward_limits(vmax: List[float], ds: List[float], dt: float) -> List[float]:
    """Apply accel/decel limits with a forward-backward pass.
    Args:
        vmax: per-point free-flow caps (m/s)
        ds:   segment distances (m) between samples (len-1)
        dt:   timestep (s)
    Returns:
        v: speed profile (len = len(vmax))
    """
    n = len(vmax)
    v = [0.0] * n
    # Forward: accelerate up to vmax with A_DRIVE
    for i in range(1, n):
        v_prev = v[i - 1]
        v_target = min(vmax[i], math.sqrt(max(v_prev ** 2 + 2 * A_DRIVE * ds[i - 1], 0.0)))
        # also constrain by dt-based accel
        v[i] = min(v_target, v_prev + A_DRIVE * dt)
    # Backward: ensure we can stop/slow using A_BRAKE
    for i in range(n - 2, -1, -1):
        v_next = v[i + 1]
        v_target = min(v[i], math.sqrt(max(v_next ** 2 + 2 * A_BRAKE * ds[i], 0.0)))
        v[i] = min(v[i], v_target, v_next + A_BRAKE * dt)
    return v


def plan_speed_profile(poly_ll: List[Tuple[float, float]], speed_limit_mps: List[float], dt: float) -> Tuple[List[float], float, float]:
    """Compute optimum speed profile along a route polyline.
    Returns (v_opt[m/s] per point, distance_km, eta_min_opt[min]).
    """
    assert len(poly_ll) >= 2, "polyline too short"
    # Normalize speed_limit list to per-point length
    if len(speed_limit_mps) == len(poly_ll) - 1:
        # make per-vertex by duplicating last segment limit
        vfree = [speed_limit_mps[0]] + speed_limit_mps[:]
    elif len(speed_limit_mps) == len(poly_ll):
        vfree = speed_limit_mps[:]
    else:
        raise ValueError("speed_limit_mps must match polyline length or segments")

    # Curvature cap
    v_capped = _cap_by_curvature(vfree, poly_ll)

    # Segment distances
    ds = []
    for i in range(len(poly_ll) - 1):
        lat1, lon1 = poly_ll[i]
        lat2, lon2 = poly_ll[i + 1]
        # rough meters (good enough; we only need ds for dynamics)
        d = polyline_length_m([ (lat1, lon1), (lat2, lon2) ])
        ds.append(d)

    # Forward-backward pass for accel/decel limits
    v_opt = _forward_backward_limits(v_capped, ds, dt)

    # Distance & ETA
    total_m = sum(ds)
    distance_km = total_m / 1000.0
    # Avoid div by 0: use max(v, 0.1 m/s) when integrating ETA
    eta_s = 0.0
    for i in range(len(ds)):
        v_seg = max((v_opt[i] + v_opt[i + 1]) * 0.5, 0.1)
        eta_s += ds[i] / v_seg
    eta_min_opt = eta_s / 60.0

    return v_opt, distance_km, eta_min_opt