import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const localCoverageFile = path.resolve(__dirname, '../coverage/lcov.info');
const rootCoverageDir = path.resolve(__dirname, '../../coverage/js');
const rootCoverageFile = path.join(rootCoverageDir, 'lcov.info');

if (!fs.existsSync(localCoverageFile)) {
  console.error(`❌ Coverage file not found at ${localCoverageFile}. Run tests with c8 first.`);
  process.exit(1);
}

const content = fs.readFileSync(localCoverageFile, 'utf-8');

// Parse LCOV to assert 100% line and branch coverage
let linesFound = 0;
let linesHit = 0;
let branchesFound = 0;
let branchesHit = 0;

for (const line of content.split('\n')) {
  if (line.startsWith('LF:')) {
    linesFound += parseInt(line.substring(3).trim(), 10);
  } else if (line.startsWith('LH:')) {
    linesHit += parseInt(line.substring(3).trim(), 10);
  } else if (line.startsWith('BRF:')) {
    branchesFound += parseInt(line.substring(4).trim(), 10);
  } else if (line.startsWith('BRH:')) {
    branchesHit += parseInt(line.substring(4).trim(), 10);
  }
}

if (linesFound === 0 || linesHit < linesFound) {
  console.error(`❌ Incomplete line coverage: ${linesHit}/${linesFound} lines hit`);
  process.exit(1);
}

if (branchesFound > 0 && branchesHit < branchesFound) {
  console.error(`❌ Incomplete branch coverage: ${branchesHit}/${branchesFound} branches hit`);
  process.exit(1);
}

fs.mkdirSync(rootCoverageDir, { recursive: true });
fs.copyFileSync(localCoverageFile, rootCoverageFile);

console.log(`✅ Verified 100% JS/TS coverage (Lines: ${linesHit}/${linesFound}, Branches: ${branchesHit}/${branchesFound})`);
console.log(`✅ Copied authentic LCOV report to: ${rootCoverageFile}`);
