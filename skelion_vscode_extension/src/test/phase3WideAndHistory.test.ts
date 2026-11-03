import * as fs from 'fs';
import * as path from 'path';
import { Conversation, ConversationSchema } from '../shared/chat.js';
import {
  exportConversationAsMarkdown,
  exportConversationAsJson,
  extractArtifactsFromConversation,
  parseSlashCommand,
  parseMentions,
} from '../shared/chatExport.js';

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`FAILED: ${msg}`);
    process.exit(1);
  }
  console.log(`✓ PASS: ${msg}`);
}

async function runPhase3Tests() {
  console.log('--- Running Phase 3: Wide View, Artifacts & History Tests ---');

  // Load golden conversation fixture
  const fixturePath = path.resolve(__dirname, '../../fixtures/golden_conversations.json');
  assert(fs.existsSync(fixturePath), 'Golden conversations fixture exists');

  const rawJson = fs.readFileSync(fixturePath, 'utf-8');
  const conversations = JSON.parse(rawJson);
  const goldenConv = ConversationSchema.parse(conversations[0]);

  // Test 1: Export to Markdown
  const mdExport = exportConversationAsMarkdown(goldenConv);
  assert(typeof mdExport === 'string' && mdExport.length > 200, 'Markdown export generated non-empty string');
  assert(mdExport.includes('# Incident Triage & Checkout 429 Storm'), 'Markdown export contains conversation title');
  assert(mdExport.includes('### Top Active Incidents'), 'Markdown export contains table title');
  assert(mdExport.includes('| Issue | Route | Affected % | Type |'), 'Markdown export formats table headers');
  assert(mdExport.includes('```diff'), 'Markdown export formats diff code blocks');
  assert(mdExport.includes('### 📈 Chart: Error rate by minute (last 24h)'), 'Markdown export contains chart summary');

  // Test 2: Export to JSON
  const jsonExport = exportConversationAsJson(goldenConv);
  const reParsed = JSON.parse(jsonExport);
  const validation = ConversationSchema.safeParse(reParsed);
  assert(validation.success, 'JSON export roundtrips cleanly through ConversationSchema');

  // Test 3: Extract Artifacts from Conversation
  const artifacts = extractArtifactsFromConversation(goldenConv);
  assert(artifacts.length >= 4, `Extracted ${artifacts.length} artifacts (expected >= 4)`);

  const chartArtifact = artifacts.find(a => a.type === 'chart');
  assert(!!chartArtifact, 'Chart artifact successfully extracted');
  assert(chartArtifact?.title === 'Error rate by minute (last 24h)', 'Chart artifact title matches');

  const tableArtifact = artifacts.find(a => a.type === 'table');
  assert(!!tableArtifact, 'Table artifact successfully extracted');
  assert(tableArtifact?.title === 'Top Active Incidents', 'Table artifact title matches');

  const diffArtifact = artifacts.find(a => a.type === 'diff');
  assert(!!diffArtifact, 'Diff artifact successfully extracted');
  assert(diffArtifact?.title === 'gossipmesh/p2p/congestion.py', 'Diff artifact filename matches');

  const incidentArtifact = artifacts.find(a => a.type === 'incident');
  assert(!!incidentArtifact, 'Incident artifact successfully extracted');

  const prConv = ConversationSchema.parse(conversations[3]);
  const prArtifacts = extractArtifactsFromConversation(prConv);
  const prArtifact = prArtifacts.find(a => a.type === 'pr');
  assert(!!prArtifact, 'PR artifact successfully extracted');
  assert(Boolean(prArtifact && prArtifact.title.includes('PR #190')), 'PR artifact title includes #190');

  // Test 4: Parse Slash Commands
  const cmdIncident = parseSlashCommand('/incident 190');
  assert(cmdIncident?.command === 'incident' && cmdIncident?.args === '190', 'Parses /incident 190 correctly');

  const cmdFix = parseSlashCommand('/fix checkout_429 --replay');
  assert(cmdFix?.command === 'fix' && cmdFix?.args === 'checkout_429 --replay', 'Parses /fix with flags correctly');

  const cmdExplain = parseSlashCommand('/explain');
  assert(cmdExplain?.command === 'explain' && cmdExplain?.args === '', 'Parses zero-arg command /explain correctly');

  const cmdAudit = parseSlashCommand('/audit full');
  assert(cmdAudit?.command === 'audit' && cmdAudit?.args === 'full', 'Parses /audit command correctly');

  const notCmd = parseSlashCommand('regular user question');
  assert(notCmd === null, 'Non-slash input returns null');

  // Test 5: Parse @ Mentions
  const mentions1 = parseMentions('Check @congestion.py and @incident_190 for details');
  assert(mentions1.includes('congestion.py') && mentions1.includes('incident_190'), 'Parses multiple mentions cleanly');

  const mentionsPath = parseMentions('See path @gossipmesh/p2p/congestion.py:260 for fix');
  assert(mentionsPath.includes('gossipmesh/p2p/congestion.py:260'), 'Parses path-style mentions cleanly');

  console.log('\nPhase 3 Tests: All passed successfully!');
}

runPhase3Tests().catch(err => {
  console.error('Phase 3 test suite failed:', err);
  process.exit(1);
});
