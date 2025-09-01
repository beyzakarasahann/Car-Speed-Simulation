"use client";

import { useMapEvents } from "react-leaflet";
import { LatLngTuple } from "leaflet";

type Props = {
  onSelectPoint: (point: LatLngTuple) => void;
};

export default function ClickHandler({ onSelectPoint }: Props) {
  useMapEvents({
    click(e) {
      console.log("🗺️ Map clicked at:", e.latlng);
      const latlng: LatLngTuple = [e.latlng.lat, e.latlng.lng];
      console.log("📍 Calling onSelectPoint with:", latlng);
      onSelectPoint(latlng);
    },
  });

  return null;
}
