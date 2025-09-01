"use client";

import { useEffect } from "react";
import { useMap } from "react-leaflet";

type Props = {
  onMapReady: (map: any) => void;
};

export default function MapRefSetter({ onMapReady }: Props) {
  const map = useMap();

  useEffect(() => {
    if (map) {
      onMapReady(map);
    }
  }, [map]);

  return null;
}
