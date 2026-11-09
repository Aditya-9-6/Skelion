import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export const ThreeCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [webglSupported, setWebglSupported] = useState(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. WebGL Support Check & Renderer Setup with Error Boundary Fallback
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      });
    } catch (err) {
      console.warn('WebGL is not available in this environment. Falling back to CSS glassmorphism UI:', err);
      setWebglSupported(false);
      return;
    }

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050811, 0.05);

    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.set(0, 0, 7);

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // 2. Dynamic Lighting
    const ambientLight = new THREE.AmbientLight(0x0c1527, 2.0);
    scene.add(ambientLight);

    const keyLight = new THREE.PointLight(0x00f2fe, 3.5, 30);
    keyLight.position.set(4, 5, 5);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0x7f00ff, 4.0, 30);
    rimLight.position.set(-5, -3, 4);
    scene.add(rimLight);

    const accentLight = new THREE.PointLight(0x00f5a0, 2.0, 25);
    accentLight.position.set(0, -4, 3);
    scene.add(accentLight);

    // 3. Parallax Pivot Group (receives smooth, bounded mouse tilt & parallax without runaway accumulation)
    const parallaxPivotGroup = new THREE.Group();
    scene.add(parallaxPivotGroup);

    // Procedural 3D Faceted Skelion Shield (position and orientation driven by GSAP ScrollTrigger)
    const shieldGroup = new THREE.Group();
    parallaxPivotGroup.add(shieldGroup);

    // Shield custom polygon geometry matching the official monogram
    const shieldShape = new THREE.Shape();
    shieldShape.moveTo(0, 1.8); // Top crest center
    shieldShape.lineTo(0.9, 1.4); // Top right corner
    shieldShape.lineTo(1.2, 0.5); // Upper right side
    shieldShape.lineTo(1.0, -0.6); // Lower right side
    shieldShape.lineTo(0, -1.8); // Bottom tip
    shieldShape.lineTo(-1.0, -0.6); // Lower left side
    shieldShape.lineTo(-1.2, 0.5); // Upper left side
    shieldShape.lineTo(-0.9, 1.4); // Top left corner
    shieldShape.closePath();

    const extrudeSettings = {
      depth: 0.35,
      bevelEnabled: true,
      bevelSegments: 3,
      steps: 1,
      bevelSize: 0.15,
      bevelThickness: 0.15,
    };

    const shieldGeo = new THREE.ExtrudeGeometry(shieldShape, extrudeSettings);
    shieldGeo.center();

    // Glass material with refraction, dispersion and transmission
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x00e5ff,
      emissive: 0x002244,
      emissiveIntensity: 0.4,
      metalness: 0.2,
      roughness: 0.1,
      transmission: 0.75,
      thickness: 1.2,
      ior: 1.52,
      transparent: true,
      opacity: 0.85,
    });

    const shieldMesh = new THREE.Mesh(shieldGeo, glassMaterial);
    shieldGroup.add(shieldMesh);

    // Wireframe edge highlight for cybernetic feel
    const edgesGeo = new THREE.EdgesGeometry(shieldGeo, 24);
    const edgesMat = new THREE.LineBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.65,
      linewidth: 2,
    });
    const edgeLines = new THREE.LineSegments(edgesGeo, edgesMat);
    shieldGroup.add(edgeLines);

    // Core floating energy emblem inside shield
    const coreGeo = new THREE.OctahedronGeometry(0.45, 0);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x7f00ff,
      emissive: 0x7f00ff,
      emissiveIntensity: 1.5,
      wireframe: true,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    shieldGroup.add(coreMesh);

    // 4. Floating Glass Shards & Polyhedral Crystals
    const crystalGroup = new THREE.Group();
    parallaxPivotGroup.add(crystalGroup);

    const crystalGeoList = [
      new THREE.IcosahedronGeometry(0.3, 0),
      new THREE.TetrahedronGeometry(0.35, 0),
      new THREE.OctahedronGeometry(0.28, 0),
    ];

    const crystalMat = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      emissive: 0x0369a1,
      emissiveIntensity: 0.2,
      metalness: 0.1,
      roughness: 0.15,
      transmission: 0.85,
      thickness: 0.8,
      ior: 1.6,
      transparent: true,
      opacity: 0.7,
    });

    const crystals: THREE.Mesh[] = [];
    const crystalCount = 18;

    for (let i = 0; i < crystalCount; i++) {
      const geo = crystalGeoList[i % crystalGeoList.length];
      const mesh = new THREE.Mesh(geo, crystalMat);

      const angle = (i / crystalCount) * Math.PI * 2;
      const radius = 2.5 + (Math.random() - 0.5) * 1.5;
      mesh.position.set(
        Math.cos(angle) * radius,
        (Math.random() - 0.5) * 4.5,
        (Math.random() - 0.5) * 3
      );

      mesh.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        Math.random() * Math.PI
      );

      const scale = 0.6 + Math.random() * 0.8;
      mesh.scale.set(scale, scale, scale);

      crystals.push(mesh);
      crystalGroup.add(mesh);
    }

    // 5. Cybernetic Starfield & Node Dust
    const particleCount = 1200;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    const c1 = new THREE.Color(0x00f2fe);
    const c2 = new THREE.Color(0x7f00ff);
    const c3 = new THREE.Color(0x00f5a0);

    for (let i = 0; i < particleCount; i++) {
      particlePositions[i * 3] = (Math.random() - 0.5) * 25;
      particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 25;
      particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 15 - 2;

      const mixColor = i % 3 === 0 ? c1 : i % 3 === 1 ? c2 : c3;
      particleColors[i * 3] = mixColor.r;
      particleColors[i * 3 + 1] = mixColor.g;
      particleColors[i * 3 + 2] = mixColor.b;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.055,
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // 6. Interactive Mouse Movement / Parallax Tracking
    let targetMouseX = 0;
    let targetMouseY = 0;
    let currentMouseX = 0;
    let currentMouseY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      targetMouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      targetMouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // 7. GSAP ScrollTrigger Integration for 3D Camera & Geometry Choreography
    // Precisely distributed across 6 sequential, non-overlapping intervals (total duration 6.0)
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: document.body,
          start: 'top top',
          end: 'bottom bottom',
          scrub: 1.2,
        },
      });

      // Section 0 -> 1: Overview -> Terms of Service (Shield moves right, tilts)
      tl.to(shieldGroup.position, { x: 2.2, y: 0.1, z: -0.5, ease: 'power1.inOut', duration: 1.0 }, 0)
        .to(shieldGroup.rotation, { x: 0.2, y: -0.65, z: -0.15, ease: 'power1.inOut', duration: 1.0 }, 0)
        .to(camera.position, { x: 0.5, y: 0, z: 6.2, ease: 'power1.inOut', duration: 1.0 }, 0)
        .to(keyLight.color, { r: 0.0, g: 0.7, b: 1.0, ease: 'power1.inOut', duration: 1.0 }, 0);

      // Section 1 -> 2: Terms -> Privacy Policy (Shield moves left, emerald tone)
      tl.to(shieldGroup.position, { x: -2.3, y: -0.2, z: -0.2, ease: 'power1.inOut', duration: 1.0 }, 1.0)
        .to(shieldGroup.rotation, { x: 0.35, y: 0.75, z: 0.1, ease: 'power1.inOut', duration: 1.0 }, 1.0)
        .to(camera.position, { x: -0.5, y: 0.1, z: 6.0, ease: 'power1.inOut', duration: 1.0 }, 1.0)
        .to(keyLight.color, { r: 0.0, g: 0.96, b: 0.63, ease: 'power1.inOut', duration: 1.0 }, 1.0);

      // Section 2 -> 3: Privacy -> Refund Policy (Shield flips, warm golden amber lighting)
      tl.to(shieldGroup.position, { x: 2.4, y: 0.3, z: -0.8, ease: 'power1.inOut', duration: 1.0 }, 2.0)
        .to(shieldGroup.rotation, { x: -0.2, y: 2.4, z: 0.2, ease: 'power1.inOut', duration: 1.0 }, 2.0)
        .to(camera.position, { x: 0.4, y: -0.1, z: 5.8, ease: 'power1.inOut', duration: 1.0 }, 2.0)
        .to(keyLight.color, { r: 1.0, g: 0.7, b: 0.0, ease: 'power1.inOut', duration: 1.0 }, 2.0);

      // Section 3 -> 4: Refund -> Security & Egress (Shield rises to top-left, intense cyan defense)
      tl.to(shieldGroup.position, { x: -2.0, y: 0.6, z: -0.4, ease: 'power1.inOut', duration: 1.0 }, 3.0)
        .to(shieldGroup.rotation, { x: 0.4, y: -0.9, z: -0.25, ease: 'power1.inOut', duration: 1.0 }, 3.0)
        .to(camera.position, { x: -0.2, y: 0.2, z: 6.4, ease: 'power1.inOut', duration: 1.0 }, 3.0)
        .to(keyLight.color, { r: 0.0, g: 0.85, b: 1.0, ease: 'power1.inOut', duration: 1.0 }, 3.0);

      // Section 4 -> 5: Security -> Open Source Licenses (Shield centers and expands with royal violet)
      tl.to(shieldGroup.position, { x: 2.1, y: -0.3, z: -0.5, ease: 'power1.inOut', duration: 1.0 }, 4.0)
        .to(shieldGroup.rotation, { x: -0.3, y: 1.2, z: 0.15, ease: 'power1.inOut', duration: 1.0 }, 4.0)
        .to(camera.position, { x: 0.3, y: -0.2, z: 6.0, ease: 'power1.inOut', duration: 1.0 }, 4.0)
        .to(keyLight.color, { r: 0.7, g: 0.2, b: 1.0, ease: 'power1.inOut', duration: 1.0 }, 4.0);

      // Section 5 -> 6: Licenses -> Grievance & Contact (Returns to welcoming center pose)
      tl.to(shieldGroup.position, { x: 0, y: -0.2, z: 0, ease: 'power1.inOut', duration: 1.0 }, 5.0)
        .to(shieldGroup.rotation, { x: 0.1, y: 0.3, z: 0.05, ease: 'power1.inOut', duration: 1.0 }, 5.0)
        .to(camera.position, { x: 0, y: 0, z: 6.6, ease: 'power1.inOut', duration: 1.0 }, 5.0)
        .to(keyLight.color, { r: 0.0, g: 0.95, b: 1.0, ease: 'power1.inOut', duration: 1.0 }, 5.0);
    });

    // 8. Animation & Render Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const render = () => {
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      // Smooth mouse lerping
      currentMouseX += (targetMouseX - currentMouseX) * 0.05;
      currentMouseY += (targetMouseY - currentMouseY) * 0.05;

      // Bounded parallax offset and tilt applied to pivot group (prevents runaway drift)
      parallaxPivotGroup.position.x = currentMouseX * 0.35;
      parallaxPivotGroup.position.y = -currentMouseY * 0.2;
      parallaxPivotGroup.rotation.y = currentMouseX * 0.12;
      parallaxPivotGroup.rotation.x = -currentMouseY * 0.08;

      // Constant gentle rotation of core and crystals
      coreMesh.rotation.x += delta * 1.2;
      coreMesh.rotation.y += delta * 1.5;

      crystals.forEach((crystal, index) => {
        crystal.rotation.x += delta * (0.3 + (index % 3) * 0.2);
        crystal.rotation.y += delta * (0.4 + (index % 2) * 0.2);
        crystal.position.y += Math.sin(elapsedTime * 1.5 + index) * 0.002;
      });

      // Slowly rotate particle field
      particles.rotation.y = elapsedTime * 0.02;
      particles.rotation.x = Math.sin(elapsedTime * 0.01) * 0.05;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    // 9. Resize Handling
    const handleResize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();

      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      ScrollTrigger.refresh();
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);

      ctx.revert();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      renderer.dispose();
      shieldGeo.dispose();
      glassMaterial.dispose();
      edgesGeo.dispose();
      edgesMat.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      crystalGeoList.forEach((g) => g.dispose());
      crystalMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
    };
  }, []);

  if (!webglSupported) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="webgl-canvas-container fixed inset-0 pointer-events-none z-0 overflow-hidden"
      aria-hidden="true"
    />
  );
};
