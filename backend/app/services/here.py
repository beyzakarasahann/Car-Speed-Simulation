import httpx
import json
from typing import List, Dict, Any, Tuple
from app.core.config import HERE_API_KEY
from app.core.logger import get_logger

log = get_logger(__name__)

async def fetch_here_route(start: Tuple[float, float], end: Tuple[float, float]) -> List[Dict[str, Any]]:
    """Fetch route from HERE API and return list of coordinate dictionaries."""
    if not HERE_API_KEY:
        log.warning("No HERE API key available, using direct route")
        return _direct_route(start, end)
    
    try:
        url = "https://router.hereapi.com/v8/routes"
        params = {
            "apikey": HERE_API_KEY,
            "origin": f"{start[0]},{start[1]}",
            "destination": f"{end[0]},{end[1]}",
            "transportMode": "car",
            "return": "polyline,summary",
            "routingMode": "fast"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            
        if response.status_code != 200:
            log.error(f"HERE API error: {response.status_code}")
            return _direct_route(start, end)
            
        data = response.json()
        log.info(f"HERE API response structure: {list(data.keys())}")
        routes = data.get("routes", [])
        
        if not routes:
            log.warning("No routes returned from HERE API")
            log.info(f"Full response: {data}")
            return _direct_route(start, end)
            
        # Get the first route
        route = routes[0]
        log.info(f"Route keys: {list(route.keys())}")
        sections = route.get("sections", [])
        log.info(f"Number of sections: {len(sections)}")
        
        coordinates = []
        for i, section in enumerate(sections):
            log.info(f"Section {i} keys: {list(section.keys())}")
            polyline = section.get("polyline", {})
            log.info(f"Polyline type: {type(polyline)}")
            
            # Handle different polyline formats
            if isinstance(polyline, dict):
                if "coordinates" in polyline:
                    coords = polyline["coordinates"]
                    log.info(f"Found coordinates: {len(coords)} points")
                    coordinates.extend(_parse_coordinates(coords))
            elif isinstance(polyline, str):
                # HERE v8 returns flexible polyline (NOT Google polyline)
                try:
                    from flexpolyline import decode as fp_decode
                    decoded = fp_decode(polyline)  # returns list of (lat, lon[, z])
                    coords = [{"lat": float(lat), "lon": float(lon)} for (lat, lon, *_) in decoded]
                    log.info(f"Decoded HERE flexible polyline points: {len(coords)}")
                    coordinates.extend(coords)
                except Exception as e:
                    log.error(f"Error decoding HERE flexible polyline: {e}")
        
        # If no coordinates found, try alternative parsing
        if not coordinates:
            log.warning("No coordinates found in polyline, trying alternative parsing")
            coordinates = _parse_alternative_route_data(route)
        
        log.info(f"HERE route: {len(coordinates)} points")
        if coordinates:
            log.info(f"First coordinate: {coordinates[0]}")
            log.info(f"Last coordinate: {coordinates[-1]}")
        
        return coordinates if coordinates else _direct_route(start, end)
        
    except Exception as e:
        log.error(f"Error fetching HERE route: {e}")
        return _direct_route(start, end)


def _parse_coordinates(coords):
    """Parse coordinates from different formats."""
    coordinates = []
    for coord in coords:
        if isinstance(coord, dict):
            # Dictionary format
            lat = coord.get("lat") or coord.get("latitude")
            lng = coord.get("lng") or coord.get("longitude") or coord.get("lon")
            if lat is not None and lng is not None:
                coordinates.append({
                    "lat": float(lat),
                    "lon": float(lng)
                })
        elif isinstance(coord, list) and len(coord) >= 2:
            # Array format [lng, lat] or [lat, lng]
            if len(coord) == 2:
                # Try both orders
                try:
                    coordinates.append({
                        "lat": float(coord[1]),
                        "lon": float(coord[0])
                    })
                except (ValueError, TypeError):
                    try:
                        coordinates.append({
                            "lat": float(coord[0]),
                            "lon": float(coord[1])
                        })
                    except (ValueError, TypeError):
                        continue
    return coordinates


def _decode_polyline(encoded):
    """Deprecated: Kept for fallback only. Prefer HERE flexible polyline decoder."""
    coordinates = []
    index = 0
    lat = 0
    lng = 0
    
    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if not byte & 0x20:
                break
        lat += ~(result >> 1) if (result & 1) else (result >> 1)
        
        # Decode longitude
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if not byte & 0x20:
                break
        lng += ~(result >> 1) if (result & 1) else (result >> 1)
        
        coordinates.append({
            "lat": lat * 1e-5,
            "lon": lng * 1e-5
        })
    
    return coordinates


def _parse_alternative_route_data(route):
    """Try alternative ways to extract route data."""
    coordinates = []
    
    # Try to get coordinates from route summary or other fields
    if "sections" in route:
        for section in route["sections"]:
            if "polyline" in section:
                polyline = section["polyline"]
                if isinstance(polyline, dict) and "coordinates" in polyline:
                    coords = polyline["coordinates"]
                    coordinates.extend(_parse_coordinates(coords))
    
    return coordinates


def _direct_route(start: Tuple[float, float], end: Tuple[float, float]) -> List[Dict[str, Any]]:
    """Create a simple direct route between two points."""
    return [
        {"lat": start[0], "lon": start[1]},
        {"lat": end[0], "lon": end[1]}
    ]
