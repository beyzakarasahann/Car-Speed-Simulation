from fastapi import APIRouter, Body
import httpx, json
from app.core.config import HERE_API_KEY, ORS_API_KEY, SIM_DIR
from app.utils.io import write_atomic_json, read_json_or
from app.core.logger import get_logger
from app.utils.geo import nearest_on_polyline

router = APIRouter()
log = get_logger(__name__)

WAYPOINTS_PATH   = SIM_DIR / "waypoints.json"
CURRENT_RUN_PATH = SIM_DIR / "current_run.json"

def _append_waypoint(p):
    arr = read_json_or(WAYPOINTS_PATH, [])
    if not isinstance(arr, list): arr=[]
    arr.append({"lat": p["lat"], "lon": p["lon"]})
    write_atomic_json(arr, WAYPOINTS_PATH)
    write_atomic_json({"route": arr, "enhanced_result": [], "statistics": {}}, CURRENT_RUN_PATH)

@router.post("/api/snap-to-road")
async def snap_to_road(payload: dict = Body(...)):
    pt = (payload or {}).get("point", {})
    try:
        lat = float(pt.get("lat")); lon = float(pt.get("lon", pt.get("lng")))
    except Exception:
        return {"lat": None, "lon": None}

    # HERE
    try:
        if HERE_API_KEY:
            url="https://matcher.hereapi.com/v8/match"
            body={"probes":[{"lat":lat,"lng":lon,"timestamp":0}]}
            async with httpx.AsyncClient(timeout=10) as client:
                r=await client.post(url, params={"apikey": HERE_API_KEY}, json=body)
            if r.status_code==200:
                data=r.json(); pts=data.get("snap") or data.get("matchedPoints") or []
                if pts: p={"lat":float(pts[0]["lat"]), "lon":float(pts[0]["lng"])}; _append_waypoint(p); return p
                if "items" in data and data["items"]:
                    pos=data["items"][0].get("position")
                    if pos: p={"lat":float(pos["lat"]), "lon":float(pos["lng"])}; _append_waypoint(p); return p
    except Exception: pass

    # ORS
    try:
        if ORS_API_KEY:
            url="https://api.openrouteservice.org/v2/snap"
            headers={"Authorization": ORS_API_KEY}
            body={"points":[[lon, lat]], "srid":4326}
            async with httpx.AsyncClient(timeout=10) as client:
                r=await client.post(url, headers=headers, json=body)
            if r.status_code==200:
                data=r.json(); feat=(data.get("features") or [{}])[0]
                coords=(feat.get("geometry") or {}).get("coordinates") or []
                if coords and len(coords)>=2:
                    lo, la = coords[0], coords[1]
                    p={"lat":float(la), "lon":float(lo)}; _append_waypoint(p); return p
    except Exception: pass

    # Fallback: direkt tıklananı yaz
    p={"lat":lat, "lon":lon}; _append_waypoint(p); return p

@router.post("/api/snap-to-road/smart")
async def snap_to_road_smart(payload: dict = Body(...)):
    pt = payload.get("point") or {}
    try:
        lat=float(pt.get("lat")); lon=float(pt.get("lon", pt.get("lng")))
    except Exception:
        return {"lat": None, "lon": None}

    # Aynı mantık, ama polyline fallback da var
    try:
        if HERE_API_KEY:
            url="https://matcher.hereapi.com/v8/match"
            body={"probes":[{"lat":lat,"lng":lon,"timestamp":0}]}
            async with httpx.AsyncClient(timeout=10) as client:
                r=await client.post(url, params={"apikey": HERE_API_KEY}, json=body)
            if r.status_code==200:
                data=r.json(); pts=data.get("snap") or data.get("matchedPoints") or []
                if pts: return {"lat":float(pts[0]["lat"]), "lon":float(pts[0]["lng"])}
                if "items" in data and data["items"]:
                    pos=data["items"][0].get("position")
                    if pos: return {"lat":float(pos["lat"]), "lon":float(pos["lng"])}
    except Exception: pass

    try:
        if ORS_API_KEY:
            url="https://api.openrouteservice.org/v2/snap"
            headers={"Authorization": ORS_API_KEY}
            body={"points":[[lon, lat]], "srid":4326}
            async with httpx.AsyncClient(timeout=10) as client:
                r=await client.post(url, headers=headers, json=body)
            if r.status_code==200:
                data=r.json(); feat=(data.get("features") or [{}])[0]
                coords=(feat.get("geometry") or {}).get("coordinates") or []
                if coords and len(coords)>=2:
                    lo, la = coords[0], coords[1]
                    return {"lat":float(la), "lon":float(lo)}
    except Exception: pass

    # Polyline fallback: mevcut current_run varsa en yakın noktayı dön
    cur = SIM_DIR / "current_run.json"
    if cur.exists():
        try:
            current = read_json_or(cur, {})
            route = current.get("route", [])
            la, lo = nearest_on_polyline(lat, lon, route)
            return {"lat": la, "lon": lo}
        except Exception:
            pass

    return {"lat": lat, "lon": lon}
