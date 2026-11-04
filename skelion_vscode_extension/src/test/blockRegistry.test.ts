import * as fs from 'fs';
import * as path from 'path';
import { BlockRegistry } from '../shared/blockRegistry.js';
import { ConversationSchema, MessageSchema, BlockSchema } from '../shared/chat.js';

export function runTests(): boolean {
  console.log('--- Running BlockRegistry & Fixture Validation Tests ---');
  let passed = 0;
  let failed = 0;

  function assert(condition: boolean, name: string) {
    if (condition) {
      console.log(`✓ PASS: ${name}`);
      passed++;
    } else {
      console.error(`✗ FAIL: ${name}`);
      failed++;
    }
  }

  // 1. Check all registered types
  const types = BlockRegistry.listTypes();
  assert(types.length >= 20, `BlockRegistry has ${types.length} types registered (expected >= 20)`);
  assert(BlockRegistry.has('markdown'), 'BlockRegistry has markdown');
  assert(BlockRegistry.has('chart'), 'BlockRegistry has chart');
  assert(BlockRegistry.has('table'), 'BlockRegistry has table');
  assert(BlockRegistry.has('fix_card'), 'BlockRegistry has fix_card');
  assert(BlockRegistry.has('pr_card'), 'BlockRegistry has pr_card');
  assert(BlockRegistry.has('stat_tiles'), 'BlockRegistry has stat_tiles');

  // 2. Validate Golden Fixtures from JSON file
  const fixturesPath = path.resolve(__dirname, '../../fixtures/golden_conversations.json');
  assert(fs.existsSync(fixturesPath), `Golden fixtures file exists at ${fixturesPath}`);

  const rawJson = fs.readFileSync(fixturesPath, 'utf-8');
  const conversations = JSON.parse(rawJson);
  assert(Array.isArray(conversations), 'Golden fixtures is an array');

  for (const conv of conversations) {
    const parseResult = ConversationSchema.safeParse(conv);
    assert(parseResult.success, `Conversation "${conv.id}" parsed cleanly with ConversationSchema`);
    if (!parseResult.success) {
      console.error('Validation error:', (parseResult as any).error);
    }
  }

  // 3. Test Unsupported Block Fallback
  const unknownBlock = {
    type: 'hyper_dimensional_matrix',
    id: 'unknown_1',
    data: [1, 2, 3],
  };
  const valResult = BlockRegistry.validate(unknownBlock);
  assert(!valResult.success, 'Unknown block flagged as non-standard');
  if (!valResult.success) {
    assert((valResult as any).fallback.type === 'unsupported', 'Unknown block normalized to unsupported fallback');
  }

  // 4. Test Valid Block Parse via BlockRegistry
  const validMd = {
    type: 'markdown',
    id: 'md_test',
    text: 'Hello world',
  };
  const validResult = BlockRegistry.validate(validMd);
  assert(validResult.success, 'Valid markdown block passes BlockRegistry validation');

  console.log(`\nTest Summary: ${passed} passed, ${failed} failed.`);
  return failed === 0;
}

if (require.main === module) {
  const success = runTests();
  process.exit(success ? 0 : 1);
}
