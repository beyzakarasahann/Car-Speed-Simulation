from typing import List, Dict
import httpx
from app.core.config import OPEN_METEO_BASE
from app.core.logger import get_logger

logger = get_logger(__name__)

async def fetch_elevation_batch(coords: List[Dict[str, float]]) -> List[Dict[str, float]]:
    results = []
    batch_size = 50
    async with httpx.AsyncClient(timeout=20) as client:
        for i in range(0, len(coords), batch_size):
            batch = coords[i:i + batch_size]
            if not batch:
                continue
            lats = ",".join([str(c["lat"]) for c in batch])
            lons = ",".join([str(c["lon"]) for c in batch])
            try:
                r = await client.get(OPEN_METEO_BASE, params={"latitude": lats, "longitude": lons})
                if r.status_code == 200:
                    data = r.json()
                    elevs = data.get("elevation") or []
                    for j, e in enumerate(elevs):
                        if j < len(batch):
                            out = {**batch[j]}
                            out["elevation"] = float(e) if e is not None else 0.0
                            results.append(out)
                else:
                    # başarısızsa yükseklik olmadan ekle
                    results.extend(batch)
            except Exception as e:
                logger.warning("Elevation fetch failed: %s", e)
                results.extend(batch)
    return results if results else coords
