"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { LatLngTuple } from "leaflet";
import { useMap } from "react-leaflet";

interface Props {
  position: LatLngTuple;
  children: React.ReactNode;
  /** Pixel size of the overlay box; used to center anchor on the point */
  size?: number; // default 80
  /** If true, translate so that the element's center sits on the point */
  anchorCenter?: boolean; // default true
  /** Fine-tune offset in pixels */
  offsetX?: number;
  offsetY?: number;
}

export default function LayerAnchor({ position, children, size = 80, anchorCenter = true, offsetX = 0, offsetY = 0 }: Props) {
  const map = useMap();
  const [pane, setPane] = useState<HTMLElement | null>(null);
  const elRef = useRef<HTMLDivElement | null>(null);

  // Create host element once
  if (!elRef.current) {
    const d = document.createElement("div");
    d.style.position = "absolute";
    d.style.willChange = "transform";
    d.style.pointerEvents = "none";
    elRef.current = d;
  }

  // Attach to overlay pane
  useLayoutEffect(() => {
    const p = map.getPanes().overlayPane as HTMLElement;
    setPane(p);
    p.appendChild(elRef.current!);
    return () => {
      try { p.removeChild(elRef.current!); } catch {}
    };
  }, [map]);

  // Position update
  useEffect(() => {
    if (!pane || !position) return;
    const update = () => {
      const pt = map.latLngToLayerPoint(position);
      const x = (anchorCenter ? pt.x - size / 2 : pt.x) + offsetX;
      const y = (anchorCenter ? pt.y - size / 2 : pt.y) + offsetY;
      elRef.current!.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    };
    update();
    map.on("move zoom viewreset", update);
    return () => { map.off("move zoom viewreset", update); };
  }, [pane, map, position]);

  return pane ? createPortal(children, elRef.current!) : null;
}
