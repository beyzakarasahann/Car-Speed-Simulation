"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import "leaflet/dist/leaflet.css";
import type { Map as LeafletMap, LatLngTuple } from "leaflet";
import L from "leaflet";
import MapRefSetter from "./MapRefSetter";
import { computeStableSlopeDeg, slopeDegToGradePct } from "@/utils/slope";
import BusCanvas from "./BusCanvas";
import LayerAnchor from "./LayerAnchor";
import { apiPost } from "@/utils/api";

// Dynamic imports
const MapContainer = dynamic(() => import("react-leaflet").then((m) => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then((m) => m.TileLayer), { ssr: false });
const Marker = dynamic(() => import("react-leaflet").then((m) => m.Marker), { ssr: false });
const Polyline = dynamic(() => import("react-leaflet").then((m) => m.Polyline), { ssr: false });
const Tooltip = dynamic(() => import("react-leaflet").then((m) => m.Tooltip), { ssr: false });
const CircleMarker = dynamic(() => import("react-leaflet").then((m) => m.CircleMarker), { ssr: false });
const ClickHandler = dynamic(() => import("./ClickHandler"), { ssr: false });

// Icons
const startIcon = L.icon({ iconUrl: "/icons/start.png", iconSize: [40, 40], iconAnchor: [20, 40] });
const endIcon = L.icon({ iconUrl: "/icons/finish.png", iconSize: [40, 40], iconAnchor: [20, 40] });

// Types
interface IMUData { accel_x: number; accel_y: number; accel_z: number; gyro_x: number; gyro_y: number; gyro_z: number; }
interface VehicleState { velocity_ms: number; heading_rad: number; pitch_rad: number; roll_rad: number; }
interface EnhancedPoint {
  waypoint: number; lat: number; lon: number; elevation: number;
  fused_lat: number; fused_lon: number; distance: number;
  slope_deg: number; heading_deg: number; speed_kmh: number;
  target_speed_kmh?: number; optimal_speed_kmh?: number; acceleration_ms2?: number;
  time_sec: number; imu: IMUData; vehicle_state: VehicleState;
}
interface SimulationStats { total_distance_m?: number; avg_speed_kmh?: number; duration_s?: number; }

export default function CustomMap() {
  // Component loaded check
  useEffect(() => {
    console.log("🗺️ CustomMap component loaded!");
    console.log("📍 Current location:", window.location.href);
    console.log("🌐 User agent:", navigator.userAgent);
    
    // Test backend connection (only in development)
    if (process.env.NODE_ENV === "development") {
      const testConnection = async () => {
        try {
          console.log("🔌 Testing backend connection...");
          const response = await apiPost("/api/auto-route", {
            provider: "here",
            start: { lat: 41.015, lon: 29.01 },
            end: { lat: 41.016, lon: 29.011 },
            write_output: true
          });
          console.log("✅ Backend connection test:", response.status === 200 ? "SUCCESS" : "FAILED");
          if (response.status === 200) {
            const data = await response.json();
            console.log("📊 Test data received:", {
              routePoints: data.route?.length || 0,
              enhancedPoints: data.enhanced_result?.length || 0
            });
          }
        } catch (error) {
          console.error("❌ Backend connection test failed:", error);
        }
      };
      
      // Delay test to let component fully mount
      setTimeout(testConnection, 1000);
    }
  }, []);

  // State - No default points
  const [start, setStart] = useState<LatLngTuple | null>(null);
  const [end, setEnd] = useState<LatLngTuple | null>(null);
  const [route, setRoute] = useState<LatLngTuple[]>([]);
  const [enhancedData, setEnhancedData] = useState<EnhancedPoint[]>([]);
  const [stats, setStats] = useState<SimulationStats>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Vehicle render state
  const [busPosition, setBusPosition] = useState<LatLngTuple | null>(null);
  const [overlayYaw, setOverlayYaw] = useState(0);

  // HUD values (we’ll also write into DOM in the loop)
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [targetSpeed, setTargetSpeed] = useState(0);
  const [accel, setAccel] = useState(0);
  const [headingDeg, setHeadingDeg] = useState(0);

  // Sim flags
  const [isSimulating, setIsSimulating] = useState(false);

  // Map & animation refs
  const mapRef = useRef<LeafletMap | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const isSimulatingRef = useRef(false);
  const lastTimeRef = useRef(0);
  const timeAccRef = useRef(0);

  // Route geometry (meters)
  const segMetersRef = useRef<number[]>([]);
  const cumMetersRef = useRef<number[]>([]);
  const totalMetersRef = useRef(0);

  // Target speed resampled to route geometry (m/s, length = route.length)
  const targetMsRef = useRef<number[]>([]);
  const enhCumRef = useRef<number[]>([]); // cumulative distances for enhanced points

  // Simulation state
  const sRef = useRef(0);               // arc-length position (m)
  const vRef = useRef(0);               // current speed (m/s)
  const aRef = useRef(0);               // current accel (m/s²)
  const yawRef = useRef(0);             // filtered yaw (rad)
  const prevVRef = useRef(0);           // previous speed for dv/dt verification
  // Stable slope/grade buffers
  const slopeDegRef = useRef<number[]>([]);
  const gradePctRef = useRef<number[]>([]);
  const slopeStepRef = useRef<number>(10);

  // Physics limits (realistic bus values)
  const DT = 0.03;           // 33 Hz - optimal balance for realism
  const MAX_ACCEL = 1.8;     // m/s² (realistic bus acceleration)
  const MAX_BRAKE = -3.5;    // m/s² (realistic bus braking)
  const MAX_JERK = 1.5;      // m/s³ (comfort jerk limit)
  const KP_SPEED = 0.25;     // moderate speed control for realistic movement

  // Haversine
  const haversineM = (a: LatLngTuple, b: LatLngTuple) => {
    const R = 6371000;
    const dLat = (b[0] - a[0]) * Math.PI / 180;
    const dLon = (b[1] - a[1]) * Math.PI / 180;
    const s1 = Math.sin(dLat / 2), s2 = Math.sin(dLon / 2);
    const aa = s1 * s1 + Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * s2 * s2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(aa)));
  };

  // Keep Leaflet crisp on resize
  const hostRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!hostRef.current) return;
    const ro = new ResizeObserver(() => mapRef.current?.invalidateSize(false));
    ro.observe(hostRef.current);
    const id = setTimeout(() => mapRef.current?.invalidateSize(false), 150);
    return () => { ro.disconnect(); clearTimeout(id); };
  }, []);

  // Point select (snap if possible)
  const handlePointSelect = useCallback(async (pt: LatLngTuple) => {
    if (start && end) return;
    setError(null);
    try {
      const r = await apiPost("/api/snap-to-road", {
        point: { lat: pt[0], lon: pt[1] }
      });
      const d = await r.json();
      const snapped: LatLngTuple = [d.lat, d.lon];
      if (!start) setStart(snapped); else setEnd(snapped);
    } catch {
      if (!start) setStart(pt); else setEnd(pt);
    }
  }, [start, end]);

  // Fetch route with enhanced debugging
  useEffect(() => {
    if (!start || !end) {
      console.log("No start or end points yet:", { start, end });
      return;
    }
    
    console.log("🚀 Fetching route from backend:", { start, end });
    (async () => {
      setIsLoading(true); setError(null);
      try {
        const requestBody = {
          provider: "here",
          start: { lat: start[0], lon: start[1] },
          end: { lat: end[0], lon: end[1] },
          write_output: true,
        };
        console.log("📡 API Request:", requestBody);
        
        const r = await apiPost("/api/auto-route", requestBody);
        
        console.log("📡 API Response status:", r.status);
        if (!r.ok) {
          const errorText = await r.text();
          console.error("❌ API Error:", errorText);
          throw new Error(errorText);
        }
        
        const data = await r.json();
        console.log("✅ API Response data:", {
          routePoints: data.route?.length || 0,
          enhancedPoints: data.enhanced_result?.length || 0,
          stats: data.statistics
        });

        const latlngs: LatLngTuple[] = (data.route || []).map((p: any) => [p.lat, p.lon]);
        if (latlngs.length < 2) throw new Error("Invalid route data");

        setRoute(latlngs);
        setBusPosition(latlngs[0]);
        setEnhancedData(data.enhanced_result || []);
        setStats(data.statistics || {});
        setCurrentSpeed(0);
        setTargetSpeed(0);
        
        console.log("🎯 Enhanced data sample:", (data.enhanced_result || []).slice(0, 3));
        
        console.log("🎯 State updated:", {
          routeLength: latlngs.length,
          enhancedDataLength: (data.enhanced_result || []).length,
          firstPoint: latlngs[0],
          statsKeys: Object.keys(data.statistics || {})
        });
      } catch (e: any) {
        console.error("❌ Route fetch error:", e);
        const errorMsg = e?.message || "Route failed";
        setError(errorMsg);
        
        // Show error in UI
        const errorBanner = document.getElementById("error-banner");
        if (errorBanner) {
          errorBanner.classList.remove("hidden");
          const errorText = errorBanner.querySelector("div");
          if (errorText) errorText.textContent = `Backend Error: ${errorMsg}`;
        }
      } finally { 
        setIsLoading(false); 
        console.log("🏁 Loading finished");
      }
    })();
  }, [start, end]);

  // Build route arc-length (meters) + resample target speed to route geometry
  useEffect(() => {
    console.log("🗺️ Building route geometry:", { routeLength: route.length, enhancedDataLength: enhancedData.length });
    if (route.length < 2) {
      console.log("❌ Route too short, skipping geometry build");
      return;
    }

    // Route dist
    const seg: number[] = new Array(route.length).fill(0);
    for (let i = 1; i < route.length; i++) seg[i] = haversineM(route[i - 1], route[i]);
    const cum: number[] = new Array(route.length).fill(0);
    for (let i = 1; i < seg.length; i++) cum[i] = cum[i - 1] + seg[i];
    segMetersRef.current = seg;
    cumMetersRef.current = cum;
    totalMetersRef.current = cum[cum.length - 1];

    // Enhanced cumulative (based on lat/lon to keep real geometry)
    const enhCum: number[] = [];
    if (enhancedData.length > 0) {
      enhCum.push(0);
      for (let i = 1; i < enhancedData.length; i++) {
        const a: LatLngTuple = [enhancedData[i - 1].lat, enhancedData[i - 1].lon];
        const b: LatLngTuple = [enhancedData[i].lat, enhancedData[i].lon];
        enhCum.push(enhCum[i - 1] + haversineM(a, b));
      }
    }
    enhCumRef.current = enhCum;

    // Resample target speed (m/s) onto route cum distances with smart fallback
    const tgtMs: number[] = new Array(route.length).fill(0);
    
    if (enhancedData.length >= 2) {
      // Use backend-provided enhanced data
      for (let k = 0; k < route.length; k++) {
        const s = cum[k];
        // binary search on enhCum
        let lo = 0, hi = enhCum.length - 1;
        while (lo < hi) { const mid = (lo + hi) >> 1; if (enhCum[mid] < s) lo = mid + 1; else hi = mid; }
        const i = Math.max(1, lo);
        const s0 = enhCum[i - 1], s1 = enhCum[i];
        const t = Math.max(0, Math.min(1, (s - s0) / Math.max(1e-6, s1 - s0)));
        const v0 = ((enhancedData[i - 1].target_speed_kmh ?? enhancedData[i - 1].optimal_speed_kmh ?? enhancedData[i - 1].speed_kmh) || 50) / 3.6;
        const v1 = ((enhancedData[i].target_speed_kmh ?? enhancedData[i].optimal_speed_kmh ?? enhancedData[i].speed_kmh) || 50) / 3.6;
        tgtMs[k] = (1 - t) * v0 + t * v1;
      }
      console.log("Using backend enhanced data for speed profile:", enhancedData.length, "points");
    } else {
      // Smart fallback: realistic speed profile based on route geometry
      const baseSpeed = 50 / 3.6; // 50 km/h base speed in m/s
      const citySpeed = 30 / 3.6;  // 30 km/h for tight areas
      const highwaySpeed = 80 / 3.6; // 80 km/h for straight sections
      
      for (let k = 0; k < route.length; k++) {
        let speed = baseSpeed;
        
        // Analyze local curvature and adjust speed
        if (k > 0 && k < route.length - 1) {
          const p0 = route[k - 1], p1 = route[k], p2 = route[k + 1];
          
          // Calculate turn angle (simplified)
          const dx1 = p1[1] - p0[1], dy1 = p1[0] - p0[0];
          const dx2 = p2[1] - p1[1], dy2 = p2[0] - p1[0];
          const angle1 = Math.atan2(dy1, dx1);
          const angle2 = Math.atan2(dy2, dx2);
          let turnAngle = Math.abs(angle2 - angle1);
          if (turnAngle > Math.PI) turnAngle = 2 * Math.PI - turnAngle;
          
          // Adjust speed based on curvature
          if (turnAngle > 0.3) speed = citySpeed; // Sharp turn
          else if (turnAngle > 0.1) speed = baseSpeed * 0.8; // Moderate turn
          else if (turnAngle < 0.05) speed = highwaySpeed; // Straight
        }
        
        tgtMs[k] = speed;
      }
      console.log("Using smart fallback speed profile, no enhanced data available");
    }
    
    targetMsRef.current = tgtMs;
    console.log("🚗 Target speed profile:", tgtMs.slice(0, 5).map(v => (v * 3.6).toFixed(1) + " km/h"));
    console.log("📏 Route geometry complete:", {
      totalDistance: totalMetersRef.current + "m",
      routeSegments: seg.length,
      targetSpeedPoints: tgtMs.length,
      averageSpeed: (tgtMs.reduce((sum, v) => sum + v, 0) / tgtMs.length * 3.6).toFixed(1) + " km/h"
    });

    // Reset sim
    sRef.current = 0; vRef.current = 0; aRef.current = 0; yawRef.current = 0; prevVRef.current = 0;
    setBusPosition(route[0]);
    console.log("🔄 Simulation state reset, bus positioned at start");
  }, [route, enhancedData]);

  // Compute robust slope/grade from enhancedData (if available)
  useEffect(() => {
    try {
      if (enhancedData.length >= 2) {
        const pts = enhancedData.map(p => ({ lat: p.lat, lon: p.lon, ele: p.elevation || 0 }));
        const step = 10;
        const { slopeDeg } = computeStableSlopeDeg(pts, step, 11, 0.5, 0.3);
        slopeDegRef.current = slopeDeg;
        gradePctRef.current = slopeDeg.map(slopeDegToGradePct);
        slopeStepRef.current = step;
        console.log("✅ Stable slope computed", slopeDeg.slice(0, 5).map(v => v.toFixed(2)));
      } else {
        slopeDegRef.current = [];
        gradePctRef.current = [];
      }
    } catch (e) {
      console.warn("⚠️ Stable slope computation failed:", e);
      slopeDegRef.current = [];
      gradePctRef.current = [];
    }
  }, [enhancedData]);

  // --- Real-time target speed planner ---
  const A_LAT_MAX = 2.0;      // m/s², comfort lateral acceleration
  const V_MAX_BASE = 120 / 3.6; // m/s, higher cap; backend/legal limits still apply

  const headingBetween = (p0: LatLngTuple, p1: LatLngTuple) => {
    const dy = (p1[0] - p0[0]) * Math.PI / 180;
    const dx = (p1[1] - p0[1]) * Math.PI / 180;
    return Math.atan2(dy, dx);
  };

  const computeCurvatureAtS = (s: number, lookaheadM: number) => {
    const s0 = Math.max(0, s);
    const s1 = Math.min((totalMetersRef.current || 0), s0 + Math.max(10, lookaheadM));
    const loc0 = locateByS(s0);
    const loc1 = locateByS(s1);
    const p0a = route[loc0.idx];
    const p0b = route[loc0.idx + 1] || p0a;
    const p1a = route[loc1.idx];
    const p1b = route[loc1.idx + 1] || p1a;
    const h0 = headingBetween(p0a, [
      p0a[0] + (p0b[0] - p0a[0]) * loc0.t,
      p0a[1] + (p0b[1] - p0a[1]) * loc0.t,
    ]);
    const h1 = headingBetween(p1a, [
      p1a[0] + (p1b[0] - p1a[0]) * loc1.t,
      p1a[1] + (p1b[1] - p1a[1]) * loc1.t,
    ]);
    let dpsi = h1 - h0;
    while (dpsi > Math.PI) dpsi -= 2 * Math.PI;
    while (dpsi < -Math.PI) dpsi += 2 * Math.PI;
    const ds = Math.max(1, s1 - s0);
    return Math.abs(dpsi) / ds; // curvature kappa ≈ dpsi/ds
  };

  const sampleSlopeDegAtS = (s: number) => {
    if (!enhancedData.length) return 0;
    const enhCum = enhCumRef.current;
    if (!enhCum.length) return 0;
    // binary search
    let lo = 0, hi = enhCum.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (enhCum[mid] < s) lo = mid + 1; else hi = mid; }
    const i = Math.min(enhancedData.length - 1, Math.max(0, lo));
    return enhancedData[i]?.slope_deg || 0;
  };

  // Disabled local real-time planner; backend target will be used exclusively

  // Locate along route by s
  const locateByS = (sMeters: number) => {
    const cum = cumMetersRef.current; if (cum.length === 0) return { idx: 0, t: 0 };
    const total = totalMetersRef.current || 1;
    const s = Math.max(0, Math.min(total, sMeters));
    let lo = 0, hi = cum.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cum[mid] < s) lo = mid + 1; else hi = mid; }
    const i = Math.max(1, lo);
    const prev = cum[i - 1];
    const seg = Math.max(1e-6, cum[i] - prev);
    const t = (s - prev) / seg;
    return { idx: i - 1, t: Math.max(0, Math.min(1, t)) };
  };

  // HUD writer (quick + reliable) with all speed-affecting factors
  const writeHUD = (curKmh: number, tgtKmh: number, a: number, headDeg: number, slope: number = 0, curve: number = 0, roll: number = 0, pitch: number = 0, elevation: number = 0, roadGrade: number = 0) => {
    const q = (id: string) => document.getElementById(id);
    const num = (x: number, d = 1) => (Number.isFinite(x) ? x.toFixed(d) : "—");
    
    // Main KPIs
    q("kpi-current")?.replaceChildren(document.createTextNode(num(curKmh)));
    q("kpi-target")?.replaceChildren(document.createTextNode(num(tgtKmh)));
    
    // Vehicle dynamics
    q("metric-accel")?.replaceChildren(document.createTextNode(`${a >= 0 ? "↑" : "↓"} ${num(Math.abs(a), 2)} m/s²`));
    q("metric-heading")?.replaceChildren(document.createTextNode(`${num(headDeg, 1)}°`));
    q("metric-rp")?.replaceChildren(document.createTextNode(`R: ${num(roll, 1)}° P: ${num(pitch, 1)}°`));
    
    // Road characteristics (speed affecting factors)
    q("metric-slope")?.replaceChildren(document.createTextNode(`${slope >= 0 ? "↗" : "↘"} ${num(Math.abs(slope), 1)}°`));
    q("metric-curve")?.replaceChildren(document.createTextNode(`${num(Math.abs(curve), 3)} rad/km`));
    q("metric-elevation")?.replaceChildren(document.createTextNode(`${num(elevation, 0)} m`));
    q("metric-grade")?.replaceChildren(document.createTextNode(`${roadGrade >= 0 ? "⬆" : "⬇"} ${num(Math.abs(roadGrade), 1)}%`));
    
    // Progress
    const s = sRef.current, total = totalMetersRef.current || 1;
    const pct = Math.max(0, Math.min(100, (s / total) * 100));
    const bar = q("progress-bar") as HTMLDivElement | null;
    if (bar) bar.style.width = `${pct}%`;
    q("progress-left")?.replaceChildren(document.createTextNode(`${Math.round(s)} m`));
    q("progress-right")?.replaceChildren(document.createTextNode(`${Math.round(total)} m`));
  };

  // Simulation loop
  const startSimulation = useCallback(() => {
    console.log("🎮 Start simulation clicked!");
    console.log("📊 Current state:", {
      isSimulating,
      routeLength: route.length,
      totalMeters: totalMetersRef.current,
      enhancedDataLength: enhancedData.length,
      targetSpeedArrayLength: targetMsRef.current?.length || 0,
      firstTargetSpeed: targetMsRef.current?.[0] || 0
    });
    
    if (isSimulating || route.length < 2 || totalMetersRef.current <= 0) {
      console.log("❌ Simulation conditions not met:", { 
        isSimulating, 
        routeLength: route.length, 
        totalMeters: totalMetersRef.current,
        reason: isSimulating ? "Already simulating" : route.length < 2 ? "Route too short" : "Total meters is 0"
      });
      return;
    }
    
    console.log("✅ Starting simulation with:", {
      routePoints: route.length,
      totalDistance: totalMetersRef.current + "m",
      enhancedDataPoints: enhancedData.length,
      targetSpeedProfile: targetMsRef.current.slice(0, 5).map(v => (v * 3.6).toFixed(1) + "km/h")
    });
    setIsSimulating(true);
    isSimulatingRef.current = true;
    lastTimeRef.current = performance.now();
    timeAccRef.current = 0;
    sRef.current = 0; vRef.current = 0; aRef.current = 0; yawRef.current = 0; prevVRef.current = 0;

    const loop = (now: number) => {
      const dtReal = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;
      timeAccRef.current += dtReal;

      while (timeAccRef.current >= DT) {
        // Backend target speed interpolation (km/h → m/s)
        let vTgt = 0;
        if (enhancedData.length >= 2) {
          const enhCum = enhCumRef.current;
          const s = sRef.current;
          let lo = 0, hi = enhCum.length - 1;
          while (lo < hi) { const mid = (lo + hi) >> 1; if (enhCum[mid] < s) lo = mid + 1; else hi = mid; }
          const idx = Math.max(1, lo);
          const s0 = enhCum[idx - 1], s1 = enhCum[idx];
          const tlin = Math.max(0, Math.min(1, (s - s0) / Math.max(1e-6, s1 - s0)));
          const v0 = ((enhancedData[idx - 1].target_speed_kmh ?? enhancedData[idx - 1].optimal_speed_kmh ?? enhancedData[idx - 1].speed_kmh) || 50) / 3.6;
          const v1 = ((enhancedData[idx].target_speed_kmh ?? enhancedData[idx].optimal_speed_kmh ?? enhancedData[idx].speed_kmh) || 50) / 3.6;
          vTgt = (1 - tlin) * v0 + tlin * v1;
        } else {
          // fallback: route-resampled target
          const loc = locateByS(sRef.current);
          const i = Math.max(0, Math.min(route.length - 2, loc.idx));
          vTgt = (1 - loc.t) * targetMsRef.current[i] + loc.t * targetMsRef.current[i + 1];
        }

        // Curvature-based lateral acceleration limiter (ensures slowing in turns)
        const lookaheadM = Math.max(30, vRef.current * 3.0 + 50);
        const kappa = computeCurvatureAtS(sRef.current, lookaheadM); // rad/m
        if (kappa > 1e-6) {
          const vCurveMax = Math.sqrt(A_LAT_MAX / Math.max(kappa, 1e-6)); // m/s
          // Apply envelope: obey both backend target and curve limit
          vTgt = Math.min(vTgt, Math.min(V_MAX_BASE, vCurveMax));
        } else {
          vTgt = Math.min(vTgt, V_MAX_BASE);
        }
        
        // Position calculation with precise road following
        const p = locateByS(sRef.current);
        
        // Debug target speed (first 20 meters only) - AFTER p is defined
        if (sRef.current < 20) console.log("🎯 Position:", { 
          position: sRef.current.toFixed(1), 
          idx: p.idx, 
          speed: (vRef.current * 3.6).toFixed(1),
          target: (vTgt * 3.6).toFixed(1)
        });
        
        // Jerk-limited P controller to reach target speed; UI acceleration equals dv/dt
        const speedError = vTgt - vRef.current;
        let desiredAccel = KP_SPEED * speedError;
        desiredAccel = Math.max(MAX_BRAKE, Math.min(MAX_ACCEL, desiredAccel));
        const jerkLimit = MAX_JERK * DT;
        const accelDelta = desiredAccel - aRef.current;
        if (accelDelta > jerkLimit) aRef.current += jerkLimit;
        else if (accelDelta < -jerkLimit) aRef.current -= jerkLimit;
        else aRef.current = desiredAccel;

        prevVRef.current = vRef.current;
        vRef.current = Math.max(0, vRef.current + aRef.current * DT);
        sRef.current = Math.min(totalMetersRef.current, sRef.current + vRef.current * DT);
        
        // Re-calculate position after speed/position update
        const pNew = locateByS(sRef.current);
        const p0 = route[pNew.idx], p1 = route[pNew.idx + 1];
        
        if (!p0 || !p1) continue; // safety check
        
        // Super smooth interpolation for natural movement
        const interpolationT = pNew.t;
        const smoothT = interpolationT * interpolationT * (3 - 2 * interpolationT); // smoothstep for natural acceleration/deceleration
        
        // High precision coordinate interpolation
        const lat = p0[0] + (p1[0] - p0[0]) * smoothT;
        const lon = p0[1] + (p1[1] - p0[1]) * smoothT;
        
        // Update position every frame for live movement
        if (Number.isFinite(lat) && Number.isFinite(lon)) {
          setBusPosition([lat, lon]);

        }

        // Heading calculation for smooth and accurate vehicle orientation
        const lookAheadDistance = Math.max(5, vRef.current * 1.2); // increased lookahead for smoother turns
        const look = locateByS(Math.min(totalMetersRef.current, sRef.current + lookAheadDistance));
        const la0 = route[look.idx], la1 = route[look.idx + 1];
        
        if (mapRef.current && la0 && la1) {
          // Calculate heading from GPS coordinates directly (more accurate)
          const currentGPS = [lat, lon];
          const lookAheadGPS = [
            la0[0] + (la1[0] - la0[0]) * look.t,
            la0[1] + (la1[1] - la0[1]) * look.t
          ];
          
          // Heading from map pixel space (exact visual alignment)
          const p1 = mapRef.current!.latLngToLayerPoint(L.latLng(currentGPS[0], currentGPS[1]));
          const p2 = mapRef.current!.latLngToLayerPoint(L.latLng(lookAheadGPS[0], lookAheadGPS[1]));
          let targetHeading = Math.atan2(p2.y - p1.y, p2.x - p1.x);
          
          // Unwrap angle (prevent sudden jumps)
          while (targetHeading - yawRef.current > Math.PI) targetHeading -= 2 * Math.PI;
          while (targetHeading - yawRef.current < -Math.PI) targetHeading += 2 * Math.PI;
          
          // Smooth filter for realistic vehicle turning
          const tau = 0.15; // faster response for better tracking
          const alpha = DT / (tau + DT);
          yawRef.current = yawRef.current + alpha * (targetHeading - yawRef.current);
          
          // Fixed GLB forward-axis correction for sport_car.glb
          const yawFix = 0; // keep 0; pre-rotation in BusCanvas points model to +X
          const displayYaw = yawRef.current + yawFix;
          setOverlayYaw(displayYaw);
          setHeadingDeg((yawRef.current * 180) / Math.PI);
        }

        // Calculate all metrics (use route geometry for curvature; backend for others when available)
        let slope = 0, curve = 0, roll = 0, pitch = 0, elevation = 0, roadGrade = 0;
        if (enhancedData.length > 0) {
          // Find current enhanced data point based on position
          const currentS = sRef.current;
          const enhIdx = Math.min(enhancedData.length - 1, Math.max(0, Math.floor((currentS / totalMetersRef.current) * enhancedData.length)));
          const enhPoint = enhancedData[enhIdx];
          const prevPoint = enhancedData[Math.max(0, enhIdx - 1)];
          
          if (enhPoint) {
            // Basic road characteristics
            // Prefer robust slope/grade if available
            if (slopeDegRef.current.length > 0) {
              const step = Math.max(1, slopeStepRef.current);
              const idx = Math.max(0, Math.min(slopeDegRef.current.length - 1, Math.round(currentS / step)));
              slope = slopeDegRef.current[idx] || 0;
              roadGrade = gradePctRef.current[idx] || 0;
            } else {
              slope = enhPoint.slope_deg || 0;
            }
            elevation = enhPoint.elevation || 0;
            // Curvature from route geometry (rad/km)
            const kappa = computeCurvatureAtS(currentS, Math.max(30, vRef.current * 3.0 + 50)); // rad/m
            curve = kappa * 1000.0; // rad/km
            
            // Vehicle attitude from physics
            const aLat = kappa * Math.max(0, vRef.current) * Math.max(0, vRef.current); // m/s^2
            const rollRad = Math.atan2(aLat, 9.80665); // use atan for better range
            roll = (Math.max(-0.25, Math.min(0.25, rollRad)) * 180) / Math.PI; // clamp ±~14°
            pitch = slope; // slope already in degrees
            
            // Road grade (percentage)
            if (!Number.isFinite(roadGrade) && prevPoint) {
              const elevDiff = (enhPoint.elevation || 0) - (prevPoint.elevation || 0);
              const horizDist = enhPoint.distance || 1;
              roadGrade = (elevDiff / Math.max(1, horizDist)) * 100;
            }
            
            // All data from backend - no simulation needed
          }
        }

        // HUD with all speed-affecting factors
        setCurrentSpeed(vRef.current * 3.6);
        setTargetSpeed(vTgt * 3.6);
        setAccel(aRef.current);
        writeHUD(
          vRef.current * 3.6, 
          vTgt * 3.6, 
          aRef.current, 
          (yawRef.current * 180) / Math.PI, 
          slope, 
          curve, 
          roll, 
          pitch, 
          elevation, 
          roadGrade
        );

        // End
        if (sRef.current >= totalMetersRef.current - 0.01) {
          setIsSimulating(false);
          isSimulatingRef.current = false;
          if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
          break;
        }
        timeAccRef.current -= DT;
      }
      // Continue loop only if still simulating - use a ref to get current value
      if (isSimulatingRef.current) {
        animationFrameRef.current = requestAnimationFrame(loop);
      } else {
        console.log("🛑 Animation loop stopped because isSimulating = false");
      }
    };

    console.log("🚀 Starting animation frame loop");
    animationFrameRef.current = requestAnimationFrame(loop);
  }, [route.length]); // Remove isSimulating from dependencies

  const stopSimulation = useCallback(() => {
    setIsSimulating(false);
    isSimulatingRef.current = false;
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, []);

  const resetSimulation = useCallback(() => {
    stopSimulation();
    sRef.current = 0; vRef.current = 0; aRef.current = 0; yawRef.current = 0; prevVRef.current = 0;
    if (route.length > 0) setBusPosition(route[0]);
    writeHUD(0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
  }, [route, stopSimulation]);

  const clearAll = useCallback(() => {
    resetSimulation();
    setStart(null); setEnd(null); setRoute([]);
    setEnhancedData([]); setStats({});
    setBusPosition(null); setError(null);
  }, [resetSimulation]);

  return (
    <div className="relative w-full h-full">

      
      {/* Error display */}
      {error && (
        <div className="absolute top-10 right-2 z-[2000] bg-red-500/90 backdrop-blur px-3 py-2 rounded-md text-[12px] max-w-xs shadow">
          Error: {error}
        </div>
      )}
      
      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute top-20 right-2 z-[2000] bg-sky-500/90 backdrop-blur px-3 py-2 rounded-md text-[12px] shadow">
          Loading route…
        </div>
      )}
      
      <div ref={hostRef} className="absolute inset-0">
        <MapContainer center={[41.015, 29.01]} zoom={13} scrollWheelZoom className="w-full h-full z-0">
          <MapRefSetter onMapReady={(map) => (mapRef.current = map)} />
          <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <ClickHandler onSelectPoint={handlePointSelect} />

          {start && (<Marker position={start} icon={startIcon}><Tooltip direction="top" offset={[0, -30]} permanent>START</Tooltip></Marker>)}
          {end && (<Marker position={end} icon={endIcon}><Tooltip direction="top" offset={[0, -30]} permanent>END</Tooltip></Marker>)}

          {route.length > 0 && (
            <>
              <Polyline positions={route} color="#00ff00" weight={5} opacity={0.75} />
              {/* progress slice (purely visual) */}
              {sRef.current > 0 && (
                <Polyline
                  positions={route.slice(0, Math.min(route.length, Math.max(1, locateByS(sRef.current).idx + 2)))}
                  color="#ff0000" weight={6} opacity={0.5}
                />
              )}
              {/* debug pebbles */}
              {route.filter((_, i) => i % 6 === 0).map((pt, i) => (
                <CircleMarker key={`p-${i}`} center={pt} radius={2} fillColor="#fff" fillOpacity={0.9} stroke={false} />
              ))}
            </>
          )}

          {/* Controls - Moved to right side */}
          <div className="absolute top-3 right-3 z-[1001] flex items-center gap-2 bg-black/50 backdrop-blur px-2.5 py-2 rounded-lg border border-white/10 shadow-md">
            <button 
              onClick={() => {
                console.log("🎮 Start button clicked!");
                startSimulation();
              }} 
              disabled={!route.length || isSimulating || !!error} 
              className="px-3 py-1.5 rounded-md bg-gradient-to-r from-emerald-400 to-sky-400 text-black text-xs font-semibold disabled:opacity-50 disabled:grayscale"
            >
              Start ({route.length} pts)
            </button>
            <button onClick={stopSimulation} disabled={!isSimulating} className="px-3 py-1.5 rounded-md bg-red-500 text-black text-xs font-semibold disabled:opacity-50 disabled:grayscale">Stop</button>
            <button onClick={resetSimulation} disabled={!route.length} className="px-3 py-1.5 rounded-md bg-sky-500 text-black text-xs font-semibold disabled:opacity-50 disabled:grayscale">Reset</button>
            <button onClick={clearAll} className="px-3 py-1.5 rounded-md bg-white/10 text-white text-xs font-semibold hover:bg-white/20">Clear</button>
          </div>
          
          {/* Debug info overlay */}
          <div className="absolute bottom-3 left-3 z-[1001] bg-black/60 backdrop-blur text-white px-3 py-2 rounded-md text-[11px] shadow">
            Route: {route.length} • Enhanced: {enhancedData.length} • Target: {targetMsRef.current?.length || 0}<br/>
            Simulating: {isSimulating ? "ON" : "OFF"} • Position: {busPosition ? `${busPosition[0].toFixed(6)},${busPosition[1].toFixed(6)}` : "NONE"}
          </div>

          {/* 3D bus anchored to overlay pane (perfectly aligned to green road) */}
          {busPosition && (
            <LayerAnchor position={busPosition} size={88} anchorCenter offsetY={-12}>
              <div
                style={{
                  width: 88,
                  height: 88,
                  transform: `rotate(${overlayYaw}rad)`,
                  transformOrigin: "50% 70%",
                  willChange: "transform",
                  zIndex: 1000,
                }}
              >
                <BusCanvas yaw={0} roll={0} pitch={0} modelUrl="/sports_car.glb" baseColor="#d60000" />
              </div>
            </LayerAnchor>
          )}
        </MapContainer>
      </div>
    </div>
  );
}
