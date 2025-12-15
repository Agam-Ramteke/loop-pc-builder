"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Points, PointMaterial, Float } from "@react-three/drei";
import * as THREE from "three";
import { useMotionValue, useSpring } from "framer-motion";

function ForceFieldParticles({ count = 4000 }) {
    const { viewport, size, camera } = useThree();
    const mesh = useRef<THREE.Points>(null!);
    const hover = useRef(new THREE.Vector3(0, 0, 0));

    // Store original positions and current velocities
    const [positions, originals] = useMemo(() => {
        const p = new Float32Array(count * 3);
        const o = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            // Create a field of particles
            const x = (Math.random() - 0.5) * 20;
            const y = (Math.random() - 0.5) * 20;
            const z = (Math.random() - 0.5) * 10;

            p[i * 3] = x;
            p[i * 3 + 1] = y;
            p[i * 3 + 2] = z;

            o[i * 3] = x;
            o[i * 3 + 1] = y;
            o[i * 3 + 2] = z;
        }
        return [p, o];
    }, [count]);

    useFrame((state) => {
        if (!mesh.current) return;

        // Convert mouse to world space (project onto z=0 plane ideally, or just use viewport scaling)
        // We map normalized mouse (-1 to 1) to viewport dimensions
        const x = (state.pointer.x * viewport.width) / 2;
        const y = (state.pointer.y * viewport.height) / 2;
        hover.current.set(x, y, 0);

        const positionsArray = mesh.current.geometry.attributes.position.array as Float32Array;

        for (let i = 0; i < count; i++) {
            const px = positionsArray[i * 3];
            const py = positionsArray[i * 3 + 1];
            const pz = positionsArray[i * 3 + 2];

            const ox = originals[i * 3];
            const oy = originals[i * 3 + 1];
            const oz = originals[i * 3 + 2];

            // Vector from mouse to particle
            const dx = px - hover.current.x;
            const dy = py - hover.current.y;

            // Distance squared (faster than sqrt)
            const dSq = dx * dx + dy * dy;
            const dist = Math.sqrt(dSq);

            // Force Radius
            const radius = 4;
            const force = Math.max(0, radius - dist) / radius; // 1 at center, 0 at edge

            if (force > 0) {
                // Repulsion (Anti-gravity push)
                const angle = Math.atan2(dy, dx);
                const strength = force * 0.15; // Power of repulsion

                // Swirl (tangential force)
                const swirlStrength = force * 0.05;

                positionsArray[i * 3] += Math.cos(angle) * strength + Math.sin(angle) * swirlStrength;
                positionsArray[i * 3 + 1] += Math.sin(angle) * strength - Math.cos(angle) * swirlStrength;
                positionsArray[i * 3 + 2] += force * 0.1; // Slight z-push
            }

            // Elastic return to original position (Damping)
            positionsArray[i * 3] += (ox - positionsArray[i * 3]) * 0.05;
            positionsArray[i * 3 + 1] += (oy - positionsArray[i * 3 + 1]) * 0.05;
            positionsArray[i * 3 + 2] += (oz - positionsArray[i * 3 + 2]) * 0.05;
        }

        mesh.current.geometry.attributes.position.needsUpdate = true;

        // Slow ambient rotation
        mesh.current.rotation.z += 0.001;
    });

    return (
        <Points ref={mesh} positions={positions} stride={3} frustumCulled={false}>
            <PointMaterial
                transparent
                color="#00e5ff"
                size={0.02}
                sizeAttenuation={true}
                depthWrite={false}
                opacity={0.8}
                blending={THREE.AdditiveBlending}
            />
        </Points>
    );
}

export default function Background3D() {
    return (
        <div className="fixed inset-0 z-[-1] bg-gradient-to-br from-[var(--background)] to-[#111111]">
            <Canvas
                camera={{ position: [0, 0, 5], fov: 60 }}
                dpr={[1, 2]} // Optimize for pixel ratio
                gl={{ antialias: true, alpha: true }}
            >
                <fog attach="fog" args={['#000000', 5, 15]} />
                <ambientLight intensity={0.5} />
                <ForceFieldParticles />
            </Canvas>
        </div>
    );
}
