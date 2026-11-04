// scripts/run-tests.js
// Unified test runner for Skelion VS Code extension unit & integration tests

const { execSync } = require('child_process');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');

console.log('====================================================');
console.log('🚀 Running Skelion VS Code Extension Test Suite');
console.log('====================================================\n');

const testCommands = [
  {
    name: 'Block Registry & Golden Fixtures',
    cmd: `node -e "const { runTests } = require('./out/test/blockRegistry.test.js'); if (!runTests()) process.exit(1);"`
  },
  {
    name: 'Phase 2: Data, Downsampling & Card Tests',
    cmd: 'node out/test/phase2Data.test.js'
  },
  {
    name: 'Phase 3: Wide View, Artifacts & History Tests',
    cmd: 'node out/test/phase3WideAndHistory.test.js'
  },
  {
    name: 'Phase 4: Advanced Blocks & Data Resolvers',
    cmd: 'node out/test/phase4AdvancedBlocks.test.js'
  },
  {
    name: 'Phase 5: Security, Performance & Accessibility Hardening',
    cmd: 'node out/test/phase5Hardening.test.js'
  }
];

let failed = 0;

for (const t of testCommands) {
  try {
    console.log(`▶ Running ${t.name}...`);
    execSync(t.cmd, { cwd: rootDir, stdio: 'inherit' });
    console.log(`\n`);
  } catch (err) {
    console.error(`❌ FAILED: ${t.name}`);
    failed++;
  }
}

if (failed > 0) {
  console.error(`\n❌ ${failed} test suite(s) failed.`);
  process.exit(1);
} else {
  console.log('====================================================');
  console.log('✅ ALL TEST SUITES PASSED CLEANLY (100%)');
  console.log('====================================================');
}
