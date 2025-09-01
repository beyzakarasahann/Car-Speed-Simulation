from __future__ import annotations
import math
from typing import List, Tuple

# WGS84
_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)
EARTH_R = 6371000.0  # Earth radius in meters
DEG2RAD = math.pi / 180.0  # Degrees to radians conversion
RAD2DEG = 180.0 / math.pi  # Radians to degrees conversion

LatLon = Tuple[float, float]
LatLonAlt = Tuple[float, float, float]


def haversine_m(p1: LatLon, p2: LatLon) -> float:
    """Great-circle distance (meters) ignoring altitude."""
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _A * c


def polyline_length_m(poly: List[LatLon]) -> float:
    return sum(haversine_m(poly[i], poly[i + 1]) for i in range(len(poly) - 1))


def geodetic_to_ecef(lat: float, lon: float, alt: float = 0.0) -> Tuple[float, float, float]:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    sin_lat, cos_lat = math.sin(lat_rad), math.cos(lat_rad)
    sin_lon, cos_lon = math.sin(lon_rad), math.cos(lon_rad)
    N = _A / math.sqrt(1 - _E2 * sin_lat ** 2)
    x = (N + alt) * cos_lat * cos_lon
    y = (N + alt) * cos_lat * sin_lon
    z = (N * (1 - _E2) + alt) * sin_lat
    return x, y, z


def ecef_to_enu(x: float, y: float, z: float, lat0: float, lon0: float, alt0: float = 0.0) -> Tuple[float, float, float]:
    x0, y0, z0 = geodetic_to_ecef(lat0, lon0, alt0)
    dx, dy, dz = x - x0, y - y0, z - z0
    lat0_rad = math.radians(lat0)
    lon0_rad = math.radians(lon0)
    sin_lat0, cos_lat0 = math.sin(lat0_rad), math.cos(lat0_rad)
    sin_lon0, cos_lon0 = math.sin(lon0_rad), math.cos(lon0_rad)

    t = -sin_lon0 * dx + cos_lon0 * dy  # East numerator helper
    e = -sin_lon0 * dx + cos_lon0 * dy
    n = -sin_lat0 * cos_lon0 * dx - sin_lat0 * sin_lon0 * dy + cos_lat0 * dz
    u = cos_lat0 * cos_lon0 * dx + cos_lat0 * sin_lon0 * dy + sin_lat0 * dz
    # Fix east value (reuse computed t wasn't necessary; keep explicit):
    e = -sin_lon0 * dx + cos_lon0 * dy
    return e, n, u


def lla_to_enu_series(poly: List[LatLonAlt]) -> Tuple[List[Tuple[float, float, float]], LatLonAlt]:
    """Convert series of (lat, lon, alt) to ENU meters anchored at first point.
    Returns (enu_points, anchor_lla)."""
    if not poly:
        return [], (0.0, 0.0, 0.0)
    lat0, lon0, alt0 = poly[0]
    enu = []
    for lat, lon, alt in poly:
        x, y, z = geodetic_to_ecef(lat, lon, alt)
        e, n, u = ecef_to_enu(x, y, z, lat0, lon0, alt0)
        enu.append((e, n, u))
    return enu, (lat0, lon0, alt0)


def curvature_series(poly: List[Tuple[float, float]]) -> List[float]:
    """Estimate planar curvature κ at each vertex using ENU approximation.
    κ = |dθ/ds|; we approximate via Menger curvature from triplets.
    Returns len(poly) array; endpoints are duplicated from nearest interior."""
    if len(poly) < 3:
        return [0.0 for _ in poly]
    # Convert to ENU with first point as anchor (z ignored)
    enu, _ = lla_to_enu_series([(lat, lon, 0.0) for lat, lon in poly])
    k = [0.0] * len(poly)
    for i in range(1, len(poly) - 1):
        x1, y1, _ = enu[i - 1]
        x2, y2, _ = enu[i]
        x3, y3, _ = enu[i + 1]
        a = math.hypot(x2 - x1, y2 - y1)
        b = math.hypot(x3 - x2, y3 - y2)
        c = math.hypot(x3 - x1, y3 - y1)
        area2 = abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
        if a * b * c == 0:
            k[i] = 0.0
        else:
            # Menger curvature: κ = 4 * area(triangle) / (a*b*c)
            k[i] = 2 * area2 / (a * b * c)
    k[0] = k[1]
    k[-1] = k[-2]
    return k


def nearest_on_polyline(point: LatLon, polyline: List[LatLon]) -> Tuple[LatLon, float]:
    """Find the nearest point on a polyline to a given point.
    Returns (nearest_point, distance_m)."""
    if not polyline:
        return point, 0.0
    
    min_distance = float('inf')
    nearest_point = point
    
    for i in range(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i + 1]
        
        # Calculate the nearest point on this line segment
        segment_nearest, segment_distance = nearest_on_segment(point, p1, p2)
        
        if segment_distance < min_distance:
            min_distance = segment_distance
            nearest_point = segment_nearest
    
    return nearest_point, min_distance


def nearest_on_segment(point: LatLon, p1: LatLon, p2: LatLon) -> Tuple[LatLon, float]:
    """Find the nearest point on a line segment to a given point.
    Returns (nearest_point, distance_m)."""
    lat, lon = point
    lat1, lon1 = p1
    lat2, lon2 = p2
    
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Calculate the dot product to determine if the nearest point is on the segment
    # This is a simplified approach using great circle calculations
    dlat1 = lat_rad - lat1_rad
    dlon1 = lon_rad - lon1_rad
    dlat2 = lat2_rad - lat1_rad
    dlon2 = lon2_rad - lon1_rad
    
    # Calculate the parameter t (0 <= t <= 1 for points on the segment)
    dot_product = dlat1 * dlat2 + dlon1 * dlon2
    segment_length_sq = dlat2 * dlat2 + dlon2 * dlon2
    
    if segment_length_sq == 0:
        # p1 and p2 are the same point
        return p1, haversine_m(point, p1)
    
    t = max(0, min(1, dot_product / segment_length_sq))
    
    # Calculate the nearest point on the segment
    nearest_lat = lat1_rad + t * dlat2
    nearest_lon = lon1_rad + t * dlon2
    
    nearest_point = (math.degrees(nearest_lat), math.degrees(nearest_lon))
    distance = haversine_m(point, nearest_point)
    
    return nearest_point, distance


def bearing_rad(p1: LatLon, p2: LatLon) -> float:
    """Calculate bearing from p1 to p2 in radians."""
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    bearing = math.atan2(y, x)
    return bearing


def wrap_angle(angle: float) -> float:
    """Wrap angle to [-π, π] range."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def slope_deg(p1: LatLonAlt, p2: LatLonAlt) -> float:
    """Calculate slope between two points in degrees."""
    lat1, lon1, alt1 = p1
    lat2, lon2, alt2 = p2
    
    # Calculate horizontal distance
    horizontal_dist = haversine_m((lat1, lon1), (lat2, lon2))
    
    # Calculate elevation difference
    elevation_diff = alt2 - alt1
    
    if horizontal_dist == 0:
        return 0.0
    
    # Calculate slope in degrees
    slope_rad = math.atan2(elevation_diff, horizontal_dist)
    return math.degrees(slope_rad)


def ll_to_local_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """Convert lat/lon to local x,y coordinates in meters."""
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    ref_lat_rad = math.radians(ref_lat)
    ref_lon_rad = math.radians(ref_lon)
    
    # Calculate local coordinates using ENU transformation
    x, y, _ = ecef_to_enu(
        *geodetic_to_ecef(lat, lon, 0.0),
        ref_lat, ref_lon, 0.0
    )
    
    return x, y


def local_xy_to_ll(x: float, y: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """Convert local x,y coordinates in meters to lat/lon."""
    # This is an approximation - for more accuracy, we'd need to implement the full inverse transformation
    # For now, we'll use a simple approximation based on the Earth's radius
    
    # Convert meters to degrees (approximate)
    lat_offset = y / EARTH_R * RAD2DEG
    lon_offset = x / (EARTH_R * math.cos(math.radians(ref_lat))) * RAD2DEG
    
    return ref_lat + lat_offset, ref_lon + lon_offset