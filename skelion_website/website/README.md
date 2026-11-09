# Skelion Legal & Compliance Architecture (3D Glassmorphism Web App)

> **Interactive Glassmorphism UI with 3D WebGL Scroll Animations for Skelion Platform.**  
> Built with **React 19**, **Vite 6 / 8**, **Three.js**, **GSAP ScrollTrigger**, and **Tailwind CSS**.

---

## 🌟 Architecture & Features

### 1. 🛡️ Three.js 3D WebGL Canvas (`ThreeCanvas.tsx`)
- **Procedural 3D Faceted Skelion Shield**: Extruded geometric polygonal shield with custom beveling, matching the official Skelion extension monogram.
- **Physical Glass Shaders**: Rendered with `THREE.MeshPhysicalMaterial` featuring physical transmission (0.75), roughness (0.1), metallic rim highlights (0.2), and IOR (1.52) for authentic glass refraction.
- **Floating Polyhedral Crystals**: 18 floating icosahedrons, tetrahedrons, and octahedrons drifting in 3D orbit around the central shield.
- **1,200 Node Cyber-Starfield**: Dynamic additive blending particle field with pulsing cyan, purple, and emerald node constellations.
- **Interactive Mouse Parallax**: Real-time cursor tracking smoothly interpolated via lerp for fluid 3D depth perception.

### 2. 🌀 GSAP ScrollTrigger 3D Choreography
- As the user scrolls across full-screen legal sections, GSAP ScrollTrigger orchestrates the Three.js camera position, rotation pitch/yaw/roll, shield coordinates, light intensities, and color grading:
  - **Trust Hub (§ 0)**: Central forward-facing shield, dual cyan/purple rim lights.
  - **Terms of Service (§ 1)**: Shield translates right (`x: 2.2`), rotates to display facet edges, key light shifts to deep azure.
  - **Privacy Charter (§ 2)**: Shield repositions left (`x: -2.3`), lighting transforms to cyber-emerald (`#00f5a0`) representing Zero Code Retention.
  - **Refund Policy (§ 3)**: Camera zooms in (`z: 5.8`), shield executes horizontal flip, light warms to golden amber (`#ffb300`).
  - **Security & Egress (§ 4)**: Shield ascends to elevated defensive angle, neon wireframes glow in high contrast cyan.
  - **Open Source & MIT (§ 5)**: Shards disperse into open constellation, rich ultraviolet theme (`#7f00ff`).
  - **Grievance Redressal (§ 6)**: Returns to welcoming low-center posture with balanced dual illumination.

### 3. 💎 Ultra-Modern Glassmorphism UI (`index.css`)
- **Multi-layer Frosted Panels**: `backdrop-filter: blur(20px) saturate(190%)` with obsidian-glass gradients (`rgba(13, 19, 33, 0.72)`).
- **Specular Border Highlights**: Subtle 1px borders with corner illumination and inset highlights (`inset 0 1px 1px 0 rgba(255, 255, 255, 0.18)`).
- **Responsive Header**: Pinned glass navigation bar featuring the official Skelion vector shield logo, real-time scroll progress bar, section pill indicators, and mobile glass drawer.
- **Interactive Clause Controls**:
  - Toggle between **Plain-English Summary (TL;DR)** and **Full Legal Text**.
  - Expand/collapse individual provisions or one-click Expand/Collapse All.
  - One-click copy permalink to any specific clause.
  - Global `Ctrl+K` / `Cmd+K` glass search modal across all policies.
  - One-click **Download Legal Pack (.md)** bundle generator.

---

## 📜 Full-Screen Legal Coverage

1. **Overview & Trust Hub** (`#overview`): Key trust pillars, vital metrics (100% IP retention, 0 bytes persistent code, 7-day refund guarantee, <24h SLA).
2. **Terms of Service** (`#terms`): 7 formal clauses covering acceptance, customer IP retention, autonomous agent replay verification, zero-restart billing, AUP, and India jurisdiction.
3. **Privacy Policy** (`#privacy`): Zero Code Retention (ZCR) guarantee, minimal collection, strict compliance with India DPDP Act 2023 & GDPR, and privacy opt-out respect.
4. **Refund & Cancellation Policy** (`#refund`): 7-Day Money-Back Guarantee (<10% quota usage threshold), instant self-service cancellation via Web Console, and 5-7 business day Razorpay/Stripe processing.
5. **Security & Egress Guarantee** (`#security`): Fail-open proxy architecture, TLS 1.3 + AES-256 secure storage, sandboxed MCP plugins, and safe harbor bug bounty.
6. **Open Source Licenses** (`#licenses`): Skelion core MIT License text and third-party notices (Three.js, GSAP, React, Lucide, Tailwind).
7. **Contact & Grievance Redressal** (`#contact`): Formally designated Data Protection Officer (Dahale Aditya Dnyaneshwar), statutory address (Pune, India), and 15-day resolution SLA.

---

## 🛠️ Development & Build Commands

```bash
# Navigate to the website directory
cd website

# Install dependencies
npm install

# Run Vite dev server with Hot Module Replacement (HMR)
npm run dev

# Run full TypeScript compile and production Vite build
npm run build

# Run automated verification suite (18 deep checks)
node scripts/verify-website.js

# Preview production build locally
npm run preview
```
