"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense } from "react";

type Props = {
  position: [number, number];
  angle: number;
};

function BusModel({ angle }: { angle: number }) {
  const { scene } = useGLTF("/busmodel.glb");

  return (
    <group rotation={[0, 0, -angle]}>
      <primitive object={scene} scale={0.35} />
    </group>
  );
}

export default function BusScene({ position, angle }: Props) {
  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 45 }}
      style={{ background: "transparent", width: "100%", height: "100%" }}
    >
      <ambientLight intensity={1.2} />
      <Suspense fallback={null}>
        <BusModel angle={angle} />
      </Suspense>
      <OrbitControls enableZoom={false} enablePan={false} />
    </Canvas>
  );
}
