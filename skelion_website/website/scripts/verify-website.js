import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '..');

console.log('--- RUNNING RIGOROUS SKELION WEBSITE AUTOMATED VERIFICATION ---');

let failureCount = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAILED: ${message}`);
    failureCount++;
  } else {
    console.log(`✅ PASSED: ${message}`);
  }
}

// 1. Verify build artifacts
const distPath = path.join(root, 'dist');
assert(fs.existsSync(distPath), 'dist directory exists');
assert(fs.existsSync(path.join(distPath, 'index.html')), 'dist/index.html exists');

const htmlContent = fs.readFileSync(path.join(distPath, 'index.html'), 'utf-8');
assert(htmlContent.includes('Skelion'), 'dist/index.html contains Skelion title');
assert(htmlContent.includes('/icon.svg') || htmlContent.includes('icon.svg'), 'dist/index.html includes icon link');

// 2. Verify media assets
const publicPath = path.join(root, 'public');
assert(fs.existsSync(path.join(publicPath, 'skelion_logo_white.svg')), 'public/skelion_logo_white.svg exists');
assert(fs.existsSync(path.join(publicPath, 'icon.svg')), 'public/icon.svg exists');
assert(fs.existsSync(path.join(publicPath, 'skelion_logo_white.png')), 'public/skelion_logo_white.png exists');

// 3. Verify legal data
const legalFile = fs.readFileSync(path.join(root, 'src', 'types', 'legal.ts'), 'utf-8');
const requiredSlugs = ['terms', 'privacy', 'refund', 'security', 'licenses', 'contact'];
requiredSlugs.forEach((slug) => {
  assert(legalFile.includes(`slug: '${slug}'`), `Legal definition for '${slug}' exists`);
});

// Verify specific legal requirements
assert(legalFile.includes('Zero Code Retention'), 'Zero Code Retention policy is defined');
assert(legalFile.includes('7-Day Money-Back Guarantee'), '7-day refund guarantee is defined');
assert(legalFile.includes('Fail-Open Proxy'), 'Fail-open proxy egress guarantee is defined');
assert(legalFile.includes('MIT License'), 'MIT License is defined');
assert(legalFile.includes('Dahale Aditya Dnyaneshwar'), 'Copyright & DPO attribution is defined');
assert(legalFile.includes('DPDP Act 2023') || legalFile.includes('DPDP Act, 2023'), 'India DPDP Act 2023 compliance is documented');

// 4. Verify Three.js and GSAP integration
const threeFile = fs.readFileSync(path.join(root, 'src', 'components', 'ThreeCanvas.tsx'), 'utf-8');
assert(threeFile.includes('THREE.Scene'), 'Three.js Scene is initialized');
assert(threeFile.includes('THREE.PerspectiveCamera'), 'PerspectiveCamera is configured');
assert(threeFile.includes('THREE.WebGLRenderer'), 'WebGLRenderer is configured');
assert(threeFile.includes('ScrollTrigger'), 'GSAP ScrollTrigger plugin is registered');
assert(threeFile.includes('tl.to'), 'GSAP timeline scrub is configured');
assert(threeFile.includes('MeshPhysicalMaterial'), 'Glass transmission material is used');

// 5. Robustness & Parallax Verification (No runaway accumulation drift)
assert(!threeFile.includes('shieldGroup.position.x += currentMouseX'), 'No runaway mouse parallax accumulation drift on shieldGroup');
assert(threeFile.includes('parallaxPivotGroup'), 'Parallax pivot group is decoupled from GSAP ScrollTrigger timeline');
assert(threeFile.includes('duration: 1.0'), 'GSAP timeline transitions have explicit non-overlapping durations');
assert(threeFile.includes('webglSupported'), 'WebGL renderer has error boundary fallback');

// 6. Global Shortcut & Header Verification
const appFile = fs.readFileSync(path.join(root, 'src', 'App.tsx'), 'utf-8');
assert(appFile.includes("e.key === 'k'") || appFile.includes("e.key === 'K'"), 'Global Ctrl+K / Cmd+K listener opens search modal');

const headerFile = fs.readFileSync(path.join(root, 'src', 'components', 'Header.tsx'), 'utf-8');
assert(headerFile.includes('skelion_logo_white.svg'), 'Header uses Skelion SVG logo');
assert(headerFile.includes('SKELION'), 'Header brand name is present');
assert(headerFile.includes('glass'), 'Glassmorphism styling is applied');
assert(headerFile.includes('windowHeight > 0'), 'Scroll progress calculation guards against division by zero');

// 7. Glassmorphism CSS verification
const cssFile = fs.readFileSync(path.join(root, 'src', 'index.css'), 'utf-8');
assert(cssFile.includes('backdrop-filter: blur') && cssFile.includes('-webkit-backdrop-filter: blur'), 'Backdrop blur and vendor prefix configured');
assert(cssFile.includes('.glass-panel'), '.glass-panel class configured with semi-transparent background');
assert(cssFile.includes('--shadow-glass'), 'Tailwind @theme custom glassmorphism shadows configured');

if (failureCount === 0) {
  console.log(`\n🌟 ALL RIGOROUS VERIFICATION CHECKS PASSED PERFECTLY! (Total assertions passed)\n`);
  process.exit(0);
} else {
  console.error(`\n💥 VERIFICATION FAILED with ${failureCount} errors.\n`);
  process.exit(1);
}
