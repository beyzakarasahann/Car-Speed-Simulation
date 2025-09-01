"use client";

import { useGLTF } from "@react-three/drei";
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Group } from "three";

export default function BusModel() {
  const group = useRef<Group>(null);
  const { scene } = useGLTF("/sports_car.glb");

  useFrame(() => {
    if (group.current) {
      group.current.rotation.y = Math.PI; // düzeltme gerekiyorsa burayla oynarsın
    }
  });

return
}
