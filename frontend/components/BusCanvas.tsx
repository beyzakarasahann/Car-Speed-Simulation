"use client";

import * as THREE from "three";
import React, { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, Environment } from "@react-three/drei";

/* ---------- props ---------- */
type BusCanvasProps = {
  yaw: number;
  roll?: number;
  pitch?: number;
  modelUrl?: string;
  baseColor?: string;
};

/* ---------- helpers ---------- */
function damp(a: number, b: number, lambda: number, dt: number) {
  return THREE.MathUtils.damp(a, b, lambda, dt);
}

/* ---------- 3D model ---------- */
type VehicleModelProps = Required<Omit<BusCanvasProps, "modelUrl" | "baseColor">> & {
  bodyColor: string;
  modelUrl: string;
};

function VehicleModel({ yaw, roll, pitch, bodyColor, modelUrl }: VehicleModelProps) {
  const { scene } = useGLTF(modelUrl);
  const grp = useRef<THREE.Group>(null);

  // Materials
  useMemo(() => {
    const body = new THREE.Color(bodyColor);
    const windowColor = new THREE.Color("#1f2937");
    const tireColor = new THREE.Color("#111827");

    scene.traverse((obj: any) => {
      if (obj.isMesh) {
        const names = (Array.isArray(obj.material) ? obj.material.map((m: any) => m?.name || "") : [obj.material?.name || ""]).join(" ").toLowerCase();
        let out: THREE.Material;
        if (names.includes("glass") || names.includes("window")) {
          out = new THREE.MeshPhysicalMaterial({ color: windowColor, metalness: 0.1, roughness: 0.25, transmission: 0.06, thickness: 0.06, clearcoat: 0.35, clearcoatRoughness: 0.25 });
        } else if (names.includes("wheel") || names.includes("tire")) {
          out = new THREE.MeshStandardMaterial({ color: tireColor, metalness: 0.2, roughness: 0.8 });
        } else {
          out = new THREE.MeshStandardMaterial({ color: body, metalness: 0.25, roughness: 0.6 });
        }
        (obj as THREE.Mesh).material = out;
        (obj as THREE.Mesh).castShadow = true;
        (obj as THREE.Mesh).receiveShadow = true;
      }
    });
  }, [scene, bodyColor]);

  // Recenter pivot to geometric center for correct rotations
  useEffect(() => {
    const bbox = new THREE.Box3().setFromObject(scene);
    const center = new THREE.Vector3();
    bbox.getCenter(center);
    scene.position.sub(center);
  }, [scene]);

  // Ensure rotation order YXZ (yaw→pitch→roll style)
  useEffect(() => {
    if (grp.current) grp.current.rotation.order = "YXZ";
  }, []);

  // Smooth orientation with proper coordinate system
  const disp = useRef({ yaw: 0, pitch: 0, roll: 0 });
  useFrame((_, dt) => {
    disp.current.yaw   = damp(disp.current.yaw,   yaw,   15, dt); // faster response
    disp.current.pitch = damp(disp.current.pitch, pitch, 12, dt);
    disp.current.roll  = damp(disp.current.roll,  roll,  12, dt);
    if (grp.current) {
      // Apply rotations in correct order for vehicle orientation
      // Y-axis rotation for yaw (turning left/right)
      grp.current.rotation.set(disp.current.pitch, disp.current.yaw, disp.current.roll);
    }
  });

  return (
    <group ref={grp} position={[0, 0, 0]} scale={0.5}>
      {/* Pre-rotate so car faces +X (right) for overlay yaw */}
      <group rotation={[0, Math.PI / 2, 0]}>
        <primitive object={scene} />
      </group>
    </group>
  );
}

/* ---------- Canvas wrapper ---------- */
const BusCanvas: React.FC<BusCanvasProps> = ({
  yaw,
  roll = 0,
  pitch = 0,
  modelUrl = "/sports_car.glb",
  baseColor = "#000000",
}) => {
  return (
    <Canvas
      frameloop="demand"
      camera={{ position: [0, 2.5, 3.5], fov: 50, zoom: 1 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      style={{ width: "100%", height: "100%" }}
    >
      <ambientLight intensity={1.1} />
      <directionalLight position={[4, 6, 4]} intensity={1.25} />
      <Suspense fallback={null}>
        <Environment preset="city" />
        <VehicleModel
          yaw={0}
          roll={0}
          pitch={0}
          bodyColor={baseColor}
          modelUrl={modelUrl}
        />
      </Suspense>
    </Canvas>
  );
};

export default BusCanvas;
// Preload common models to avoid initial flicker
useGLTF.preload("/sports_car.glb");

