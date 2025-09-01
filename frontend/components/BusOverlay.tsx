"use client";

import { useEffect, useState } from "react";
import BusScene from "./BusScene";
import L from "leaflet";

type Props = {
  position: [number, number];
  angle: number;
};

export default function BusOverlay({ position, angle }: Props) {
  const [map, setMap] = useState<any>(null);
  const [pixelPos, setPixelPos] = useState<[number, number]>([0, 0]);

  // ✅ internal state kullan, prop gelince sadece değiştir
  const [internalPos, setInternalPos] = useState(position);
  const [internalAngle, setInternalAngle] = useState(angle);

  useEffect(() => {
    setInternalPos(position);
    setInternalAngle(angle);
  }, [position, angle]);

  useEffect(() => {
    const interval = setInterval(() => {
      const el = document.querySelector(".leaflet-container") as HTMLElement;
      if (el && (el as any)._leaflet_map) {
        clearInterval(interval);
        setMap((el as any)._leaflet_map);
      }
    }, 200);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!map) return;
    const updatePixel = () => {
      const point = map.project(L.latLng(internalPos)).round();
      const size = map.getSize();
      const canvasX = point.x - size.x / 2;
      const canvasY = point.y - size.y / 2;
      setPixelPos([canvasX, canvasY]);
    };
    updatePixel();
    map.on("move zoom", updatePixel);
    return () => map.off("move zoom", updatePixel);
  }, [map, internalPos]);

  return (
    <div
      style={{
        position: "absolute",
        left: pixelPos[0],
        top: pixelPos[1],
        width: "100px",
        height: "100px",
        pointerEvents: "none",
        zIndex: 500,
      }}
    >
      <BusScene position={internalPos} angle={internalAngle} />
    </div>
  );
}
