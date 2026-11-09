import React, { useEffect, useRef } from 'react';

interface Point3D {
  x: number;
  y: number;
  z: number;
}

interface Polyhedron {
  x: number;
  y: number;
  z: number;
  baseY: number;
  rotX: number;
  rotY: number;
  rotZ: number;
  speedX: number;
  speedY: number;
  speedZ: number;
  size: number;
  vertices: Point3D[];
  edges: [number, number][];
  color: string;
  glowColor: string;
}

export const Canvas3DScene: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Mouse parallax state
    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;

    // Scroll state with smooth damping
    let scrollY = window.scrollY;
    let targetScrollY = window.scrollY;
    let scrollVelocity = 0;

    const handleResize = () => {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.scale(dpr, dpr);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const handleScroll = () => {
      targetScrollY = window.scrollY;
    };
    window.addEventListener('scroll', handleScroll, { passive: true });

    const handleMouseMove = (e: MouseEvent) => {
      targetMouseX = (e.clientX / width - 0.5) * 2;
      targetMouseY = (e.clientY / height - 0.5) * 2;
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Polyhedron generation helpers
    const createOctahedron = (size: number): { vertices: Point3D[]; edges: [number, number][] } => {
      const vertices: Point3D[] = [
        { x: 0, y: -size, z: 0 },
        { x: size, y: 0, z: 0 },
        { x: 0, y: 0, z: size },
        { x: -size, y: 0, z: 0 },
        { x: 0, y: 0, z: -size },
        { x: 0, y: size, z: 0 },
      ];
      const edges: [number, number][] = [
        [0, 1], [0, 2], [0, 3], [0, 4],
        [5, 1], [5, 2], [5, 3], [5, 4],
        [1, 2], [2, 3], [3, 4], [4, 1],
      ];
      return { vertices, edges };
    };

    const createIcosahedron = (size: number): { vertices: Point3D[]; edges: [number, number][] } => {
      const phi = (1 + Math.sqrt(5)) / 2;
      const a = size / Math.sqrt(1 + phi * phi);
      const b = a * phi;

      const rawVertices: Point3D[] = [
        { x: -a, y: b, z: 0 },
        { x: a, y: b, z: 0 },
        { x: -a, y: -b, z: 0 },
        { x: a, y: -b, z: 0 },
        { x: 0, y: -a, z: b },
        { x: 0, y: a, z: b },
        { x: 0, y: -a, z: -b },
        { x: 0, y: a, z: -b },
        { x: b, y: 0, z: -a },
        { x: b, y: 0, z: a },
        { x: -b, y: 0, z: -a },
        { x: -b, y: 0, z: a },
      ];

      // Generate edges based on distance
      const edges: [number, number][] = [];
      const edgeThreshold = a * 2.05;
      for (let i = 0; i < rawVertices.length; i++) {
        for (let j = i + 1; j < rawVertices.length; j++) {
          const dx = rawVertices[i].x - rawVertices[j].x;
          const dy = rawVertices[i].y - rawVertices[j].y;
          const dz = rawVertices[i].z - rawVertices[j].z;
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (dist < edgeThreshold) {
            edges.push([i, j]);
          }
        }
      }
      return { vertices: rawVertices, edges };
    };

    const createCube = (size: number): { vertices: Point3D[]; edges: [number, number][] } => {
      const s = size / 2;
      const vertices: Point3D[] = [
        { x: -s, y: -s, z: -s },
        { x: s, y: -s, z: -s },
        { x: s, y: s, z: -s },
        { x: -s, y: s, z: -s },
        { x: -s, y: -s, z: s },
        { x: s, y: -s, z: s },
        { x: s, y: s, z: s },
        { x: -s, y: s, z: s },
      ];
      const edges: [number, number][] = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7],
      ];
      return { vertices, edges };
    };

    // Instantiate 3D polyhedra floating across the entire vertical scroll extent
    const polyhedra: Polyhedron[] = [
      {
        x: -320,
        y: -100,
        z: 150,
        baseY: -100,
        rotX: 0.2,
        rotY: 0.4,
        rotZ: 0,
        speedX: 0.008,
        speedY: 0.012,
        speedZ: 0.005,
        size: 75,
        ...createIcosahedron(75),
        color: 'rgba(6, 182, 212, 0.75)',
        glowColor: 'rgba(6, 182, 212, 0.25)',
      },
      {
        x: 340,
        y: 80,
        z: 80,
        baseY: 80,
        rotX: 0.5,
        rotY: 0.2,
        rotZ: 0.1,
        speedX: -0.01,
        speedY: 0.015,
        speedZ: 0.007,
        size: 90,
        ...createOctahedron(90),
        color: 'rgba(147, 51, 234, 0.75)',
        glowColor: 'rgba(147, 51, 234, 0.25)',
      },
      {
        x: -280,
        y: 550,
        z: 220,
        baseY: 550,
        rotX: 0.1,
        rotY: -0.3,
        rotZ: 0.2,
        speedX: 0.012,
        speedY: -0.009,
        speedZ: 0.006,
        size: 65,
        ...createCube(65),
        color: 'rgba(59, 130, 246, 0.7)',
        glowColor: 'rgba(59, 130, 246, 0.2)',
      },
      {
        x: 320,
        y: 950,
        z: 180,
        baseY: 950,
        rotX: -0.2,
        rotY: 0.5,
        rotZ: -0.1,
        speedX: -0.007,
        speedY: 0.011,
        speedZ: -0.005,
        size: 75,
        ...createIcosahedron(75),
        color: 'rgba(16, 185, 129, 0.75)',
        glowColor: 'rgba(16, 185, 129, 0.25)',
      },
      {
        x: -240,
        y: 1500,
        z: 120,
        baseY: 1500,
        rotX: 0.3,
        rotY: 0.1,
        rotZ: 0.4,
        speedX: 0.009,
        speedY: 0.013,
        speedZ: 0.008,
        size: 85,
        ...createOctahedron(85),
        color: 'rgba(236, 72, 153, 0.75)',
        glowColor: 'rgba(236, 72, 153, 0.25)',
      },
      {
        x: 290,
        y: 2000,
        z: 230,
        baseY: 2000,
        rotX: -0.4,
        rotY: -0.2,
        rotZ: 0.1,
        speedX: 0.014,
        speedY: -0.01,
        speedZ: 0.005,
        size: 70,
        ...createCube(70),
        color: 'rgba(6, 182, 212, 0.7)',
        glowColor: 'rgba(6, 182, 212, 0.2)',
      },
      {
        x: -310,
        y: 2600,
        z: 170,
        baseY: 2600,
        rotX: 0.2,
        rotY: 0.3,
        rotZ: -0.2,
        speedX: 0.008,
        speedY: 0.012,
        speedZ: -0.006,
        size: 80,
        ...createIcosahedron(80),
        color: 'rgba(147, 51, 234, 0.75)',
        glowColor: 'rgba(147, 51, 234, 0.25)',
      },
      {
        x: 270,
        y: 3200,
        z: 140,
        baseY: 3200,
        rotX: -0.3,
        rotY: 0.4,
        rotZ: 0.2,
        speedX: -0.01,
        speedY: 0.01,
        speedZ: 0.007,
        size: 85,
        ...createOctahedron(85),
        color: 'rgba(16, 185, 129, 0.75)',
        glowColor: 'rgba(16, 185, 129, 0.25)',
      },
      {
        x: -260,
        y: 3800,
        z: 210,
        baseY: 3800,
        rotX: 0.4,
        rotY: -0.2,
        rotZ: 0.3,
        speedX: 0.011,
        speedY: -0.008,
        speedZ: 0.005,
        size: 65,
        ...createCube(65),
        color: 'rgba(6, 182, 212, 0.75)',
        glowColor: 'rgba(6, 182, 212, 0.25)',
      },
      {
        x: 300,
        y: 4300,
        z: 160,
        baseY: 4300,
        rotX: -0.1,
        rotY: 0.5,
        rotZ: -0.3,
        speedX: -0.008,
        speedY: 0.014,
        speedZ: -0.006,
        size: 80,
        ...createIcosahedron(80),
        color: 'rgba(236, 72, 153, 0.75)',
        glowColor: 'rgba(236, 72, 153, 0.25)',
      },
    ];

    // 3D Particles constellation
    interface Particle3D {
      x: number;
      y: number;
      z: number;
      vx: number;
      vy: number;
      vz: number;
      radius: number;
      alpha: number;
      hue: number;
    }

    const particleCount = 70;
    const particles: Particle3D[] = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: (Math.random() - 0.5) * 1200,
        y: (Math.random() - 0.2) * 2200,
        z: Math.random() * 600 - 100,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        vz: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 2 + 1,
        alpha: Math.random() * 0.4 + 0.2,
        hue: Math.random() > 0.5 ? 188 : 270, // Cyan or Violet
      });
    }

    // 3D Perspective Projection Function
    const project = (
      p: Point3D,
      camX: number,
      camY: number,
      camZ: number,
      fov: number
    ): { x: number; y: number; scale: number; visible: boolean } => {
      const relX = p.x - camX;
      const relY = p.y - camY;
      const relZ = p.z - camZ;

      if (relZ <= -fov + 10) {
        return { x: 0, y: 0, scale: 0, visible: false };
      }

      const scale = fov / (fov + relZ);
      const projX = width / 2 + relX * scale;
      const projY = height / 2 + relY * scale;

      return {
        x: projX,
        y: projY,
        scale,
        visible: scale > 0 && projX >= -100 && projX <= width + 100 && projY >= -100 && projY <= height + 100,
      };
    };

    // 3D Rotation helper
    const rotatePoint = (p: Point3D, rx: number, ry: number, rz: number): Point3D => {
      // Rotate around X
      let y1 = p.y * Math.cos(rx) - p.z * Math.sin(rx);
      let z1 = p.y * Math.sin(rx) + p.z * Math.cos(rx);

      // Rotate around Y
      let x2 = p.x * Math.cos(ry) + z1 * Math.sin(ry);
      let z2 = -p.x * Math.sin(ry) + z1 * Math.cos(ry);

      // Rotate around Z
      let x3 = x2 * Math.cos(rz) - y1 * Math.sin(rz);
      let y3 = x2 * Math.sin(rz) + y1 * Math.cos(rz);

      return { x: x3, y: y3, z: z2 };
    };

    let lastTime = performance.now();

    const render = (time: number) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;

      // Smooth mouse interpolation
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      // Smooth scroll interpolation
      const prevScroll = scrollY;
      scrollY += (targetScrollY - scrollY) * 0.08;
      scrollVelocity = (scrollY - prevScroll) * 0.05;

      // Camera coordinates influenced by scroll and mouse
      const camX = mouseX * 80;
      // Convert scroll pixels into 3D world vertical movement
      const camY = scrollY * 0.45 + mouseY * 40;
      const camZ = -200 + Math.sin(time * 0.0008) * 30;
      const fov = 450;

      // Clear full canvas buffer accurately
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.restore();

      // Render 3D Perspective Ground Grid (anchored relative to camera so it persists across entire page scroll)
      const gridPlaneY = camY + 450; // Follows camera depth below viewport
      const gridSpacing = 65;
      const gridCols = 24;
      const gridRows = 16;
      const scrollOffsetZ = (scrollY * 0.8) % gridSpacing;

      ctx.lineWidth = 1;

      // Draw Depth Grid Lines
      for (let c = -gridCols / 2; c <= gridCols / 2; c++) {
        const xWorld = c * gridSpacing + mouseX * 40;
        const p1 = project({ x: xWorld, y: gridPlaneY, z: -100 + scrollOffsetZ }, camX, camY, camZ, fov);
        const p2 = project({ x: xWorld, y: gridPlaneY, z: gridRows * gridSpacing + scrollOffsetZ }, camX, camY, camZ, fov);

        if (p1.visible && p2.visible) {
          const grad = ctx.createLinearGradient(p1.x, p1.y, p2.x, p2.y);
          grad.addColorStop(0, 'rgba(6, 182, 212, 0.18)');
          grad.addColorStop(0.6, 'rgba(147, 51, 234, 0.08)');
          grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
          ctx.strokeStyle = grad;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }

      // Draw Horizontal Grid Lines
      for (let r = 0; r <= gridRows; r++) {
        const zWorld = r * gridSpacing - scrollOffsetZ;
        const pLeft = project({ x: (-gridCols / 2) * gridSpacing + mouseX * 40, y: gridPlaneY, z: zWorld }, camX, camY, camZ, fov);
        const pRight = project({ x: (gridCols / 2) * gridSpacing + mouseX * 40, y: gridPlaneY, z: zWorld }, camX, camY, camZ, fov);

        if (pLeft.visible && pRight.visible) {
          const fade = Math.max(0, 1 - r / gridRows);
          ctx.strokeStyle = `rgba(6, 182, 212, ${0.14 * fade})`;
          ctx.beginPath();
          ctx.moveTo(pLeft.x, pLeft.y);
          ctx.lineTo(pRight.x, pRight.y);
          ctx.stroke();
        }
      }

      // Render 3D Floating Particles across entire page height
      for (let i = 0; i < particles.length; i++) {
        const pt = particles[i];

        pt.x += pt.vx;
        pt.y += pt.vy;
        pt.z += pt.vz;

        // Wrap around boundaries dynamically relative to camera Y
        if (pt.x < -650) pt.x = 650;
        if (pt.x > 650) pt.x = -650;
        if (pt.y < camY - 500) pt.y = camY + 800;
        if (pt.y > camY + 800) pt.y = camY - 500;
        if (pt.z < -100) pt.z = 500;
        if (pt.z > 500) pt.z = -100;

        const proj = project(pt, camX, camY, camZ, fov);
        if (proj.visible) {
          const r = Math.max(0.5, pt.radius * proj.scale);
          ctx.fillStyle = `hsla(${pt.hue}, 85%, 60%, ${pt.alpha * proj.scale * 0.8})`;
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, r, 0, Math.PI * 2);
          ctx.fill();

          // Delicate glow around prominent particles
          if (r > 1.8) {
            ctx.fillStyle = `hsla(${pt.hue}, 85%, 60%, ${pt.alpha * 0.25})`;
            ctx.beginPath();
            ctx.arc(proj.x, proj.y, r * 2.5, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // Render 3D Polyhedra (Nodes) with rotation accelerated by scroll velocity
      for (let i = 0; i < polyhedra.length; i++) {
        const poly = polyhedra[i];

        // Rotation speed increases on scroll
        const scrollBoost = Math.abs(scrollVelocity) * 0.08;
        poly.rotX += (poly.speedX + Math.sign(poly.speedX) * scrollBoost) * (dt * 60);
        poly.rotY += (poly.speedY + Math.sign(poly.speedY) * scrollBoost) * (dt * 60);
        poly.rotZ += (poly.speedZ + Math.sign(poly.speedZ) * scrollBoost) * (dt * 60);

        // Gentle floating oscillation
        poly.y = poly.baseY + Math.sin(time * 0.0015 + i * 1.5) * 20;

        // Transform vertices
        const transformed: { x: number; y: number; scale: number; visible: boolean }[] = [];
        for (let j = 0; j < poly.vertices.length; j++) {
          const rotP = rotatePoint(poly.vertices[j], poly.rotX, poly.rotY, poly.rotZ);
          const worldP: Point3D = {
            x: poly.x + rotP.x,
            y: poly.y + rotP.y,
            z: poly.z + rotP.z,
          };
          transformed.push(project(worldP, camX, camY, camZ, fov));
        }

        // Draw Wireframe Edges with depth and glow
        for (let e = 0; e < poly.edges.length; e++) {
          const [idxA, idxB] = poly.edges[e];
          const vA = transformed[idxA];
          const vB = transformed[idxB];

          if (vA.visible && vB.visible) {
            const edgeScale = (vA.scale + vB.scale) / 2;

            // Outer soft glow
            ctx.strokeStyle = poly.glowColor;
            ctx.lineWidth = 3.5 * edgeScale;
            ctx.beginPath();
            ctx.moveTo(vA.x, vA.y);
            ctx.lineTo(vB.x, vB.y);
            ctx.stroke();

            // Crisp inner core line
            ctx.strokeStyle = poly.color;
            ctx.lineWidth = 1.2 * edgeScale;
            ctx.beginPath();
            ctx.moveTo(vA.x, vA.y);
            ctx.lineTo(vB.x, vB.y);
            ctx.stroke();
          }
        }

        // Draw Vertices Nodes (Gems)
        for (let v = 0; v < transformed.length; v++) {
          const vertex = transformed[v];
          if (vertex.visible) {
            const nodeRadius = 3 * vertex.scale;
            ctx.fillStyle = '#FFFFFF';
            ctx.beginPath();
            ctx.arc(vertex.x, vertex.y, nodeRadius, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = poly.color;
            ctx.beginPath();
            ctx.arc(vertex.x, vertex.y, nodeRadius * 0.65, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
      aria-hidden="true"
    >
      {/* Subtle Iridescent Background Aura Orbs */}
      <div className="absolute top-[-10%] left-[10%] w-[650px] h-[650px] rounded-full bg-gradient-to-br from-cyan-200/35 via-sky-100/25 to-transparent blur-3xl opacity-70 animate-pulse-glow" />
      <div className="absolute top-[25%] right-[5%] w-[550px] h-[550px] rounded-full bg-gradient-to-br from-purple-200/30 via-pink-100/20 to-transparent blur-3xl opacity-60" />
      <div className="absolute top-[55%] left-[5%] w-[600px] h-[600px] rounded-full bg-gradient-to-tr from-cyan-100/30 via-blue-100/25 to-transparent blur-3xl opacity-60" />
      <div className="absolute top-[80%] right-[15%] w-[700px] h-[700px] rounded-full bg-gradient-to-tl from-purple-200/30 via-sky-100/20 to-transparent blur-3xl opacity-65" />

      {/* 3D Hardware-Accelerated Interactive Canvas */}
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
      />
    </div>
  );
};

export default Canvas3DScene;
