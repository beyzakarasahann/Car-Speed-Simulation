// hooks/useProjectedPosition.ts
import { useEffect, useState } from "react";
import { useMap } from "react-leaflet";

export const useProjectedPosition = (lat: number, lng: number) => {
  const map = useMap();
  const [position, setPosition] = useState<[number, number]>([0, 0]);

  useEffect(() => {
    if (!map) return;
    const point = map.project([lat, lng], map.getZoom());
    setPosition([point.x, point.y]);
  }, [lat, lng, map]);

  return position;
};
