from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict, Any
import httpx
import flexpolyline as fp
from app.core.config import SIM_DIR, HERE_API_KEY
from app.utils.io import write_atomic_json, read_json_or
from app.services.elevation import fetch_elevation_batch
from app.services.physics import generate_physics
from app.services.simple_physics import simple_physics_generation

router = APIRouter()

@router.post("/api/auto-route")
async def auto_route(payload: dict = Body(...)):
    provider = (payload.get("provider") or "here").lower()
    s = payload.get("start") or {}; e = payload.get("end") or {}

    try:
        o_lat=float(s.get("lat")); o_lon=float(s.get("lon", s.get("lng")))
        d_lat=float(e.get("lat")); d_lon=float(e.get("lon", e.get("lng")))
    except Exception:
        raise HTTPException(400, "Invalid start/end")

    if provider not in ("", "here", "primary"):
        raise HTTPException(400, "Only provider='here' is supported in this build")

    # Fetch HERE route and decode flexible polyline to real road coordinates
    if not HERE_API_KEY:
        raise HTTPException(500, "HERE_API_KEY missing")

    base_url = "https://router.hereapi.com/v8/routes"
    url_spans = (
        f"{base_url}?transportMode=car&origin={o_lat},{o_lon}&destination={d_lat},{d_lon}"
        "&return=polyline,summary&spans=speedLimit,roadCategory,functionalClass,countryCode,segmentId"
        "&routingMode=fast"
        f"&apikey={HERE_API_KEY}"
    )
    url_simple = (
        f"{base_url}?transportMode=car&origin={o_lat},{o_lon}&destination={d_lat},{d_lon}"
        "&return=polyline,summary"
        "&routingMode=fast"
        f"&apikey={HERE_API_KEY}"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url_spans)
        if r.status_code == 400:
            # Fallback without spans (some accounts/regions reject spans)
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url_simple)
        if r.status_code != 200:
            detail = r.text[:500] if r.text else str(r.status_code)
            raise HTTPException(502, f"HERE routing failed: {r.status_code} {detail}")
        data = r.json()
        sections = (data.get("routes") or [{}])[0].get("sections") or []
        if not sections:
            raise HTTPException(502, "No routes found")

        coords: List[Dict[str, float]] = []
        # Optional attributes per decoded point
        speed_limits_kmh: List[float] = []
        functional_classes: List[int] = []
        road_categories: List[str] = []
        for sec in sections:
            poly = sec.get("polyline")
            if not poly:
                continue
            try:
                decoded = list(fp.decode(poly))
            except Exception:
                decoded = []
            # Initialize per-section limits with None
            local_limits: List[float] = [None] * len(decoded)  # type: ignore
            local_fc: List[int] = [None] * len(decoded)  # type: ignore
            local_rc: List[str] = [None] * len(decoded)  # type: ignore
            spans = sec.get("spans") or []
            # Map spans by offset → next offset
            for si, sp in enumerate(spans):
                try:
                    off = int(sp.get("offset", 0))
                except Exception:
                    off = 0
                # Parse speed limit value (km/h)
                kmh = None
                sl = sp.get("speedLimit")
                if isinstance(sl, dict):
                    v = sl.get("value") or sl.get("general")
                    kmh = float(v) if v is not None else None
                    unit = (sl.get("unit") or "KILOMETERS_PER_HOUR").upper()
                    if kmh is not None and unit.startswith("MILES"):
                        kmh *= 1.60934
                elif isinstance(sl, (int, float)):
                    kmh = float(sl)
                # Parse class/category
                fc = sp.get("functionalClass")
                try:
                    fc = int(fc) if fc is not None else None
                except Exception:
                    fc = None
                rc = sp.get("roadCategory")
                rc = str(rc) if rc is not None else None
                # Determine span end
                next_off = len(decoded)
                if si + 1 < len(spans):
                    try:
                        next_off = int(spans[si + 1].get("offset", next_off))
                    except Exception:
                        pass
                for idx in range(max(0, off), min(len(decoded), next_off)):
                    if kmh is not None:
                        local_limits[idx] = kmh
                    if fc is not None:
                        local_fc[idx] = fc
                    if rc is not None:
                        local_rc[idx] = rc
            # Append to global arrays
            for i, (lat, lon) in enumerate(decoded):
                rec = {"lat": float(lat), "lon": float(lon)}
                lim = local_limits[i]
                if lim is not None:
                    rec["speed_limit_kmh"] = float(lim)
                fc = local_fc[i]
                if fc is not None:
                    rec["functional_class"] = int(fc)
                rc = local_rc[i]
                if rc is not None:
                    rec["road_category"] = rc
                coords.append(rec)
                speed_limits_kmh.append(rec.get("speed_limit_kmh", None))
                functional_classes.append(rec.get("functional_class", None))
                road_categories.append(rec.get("road_category", None))
        if len(coords) < 2:
            # Fallback to direct line if decoding failed entirely
            coords = [{"lat": o_lat, "lon": o_lon}, {"lat": d_lat, "lon": d_lon}]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"HERE routing error: {e}")

    # Elevation
    coords = await fetch_elevation_batch(coords)

    # route.json yaz
    write_atomic_json(coords, SIM_DIR / "route.json")

    # Physics - USE SIMPLE WORKING VERSION
    try:
        print("🎯 Trying FULL navigation system...")
        result = await generate_physics(coords)
    except Exception as e:
        print(f"⚠️ Full system failed: {e}")
        print("🚀 Using SIMPLE WORKING physics system...")
        result = simple_physics_generation(coords)

    # current_run.json (tek dosya)
    write_atomic_json(result, SIM_DIR / "current_run.json")

    # Frontend beklediği shape: route+enhanced_result+statistics
    return {
        "route": [{"lat": c["lat"], "lon": c["lon"]} for c in coords],
        "enhanced_result": result.get("enhanced_result", []),
        "statistics": result.get("statistics", {})
    }

@router.post("/api/save-route")
async def save_route(payload: dict = Body(...)):
    coords = payload.get("coordinates", [])
    if not isinstance(coords, list) or len(coords) < 2:
        raise HTTPException(400, "Invalid coordinates")
    write_atomic_json(coords, SIM_DIR / "route.json")
    return {"status":"ok", "points": coords}
