import test from 'node:test';
import assert from 'node:assert/strict';
import { parseChatLines, CHAT_INVALIDATION_KEYS } from '../src/lib/chat.ts';

test('framed chat events survive partial network chunks', () => {
  const first = parseChatLines('{"type":"tool","name":"get_current_plan"}\n{"type":"do');
  assert.equal(first.events[0].type, 'tool');
  const second = parseChatLines(first.rest + 'ne","message":{"id":"1","role":"assistant","content":"预算"},"action":null}\n');
  assert.equal(second.events[0].type, 'done');
  assert.equal(second.rest, '');
});
test('chat mutations invalidate the same budget and transaction caches as the UI', () => {
  assert.ok(CHAT_INVALIDATION_KEYS.includes('budgets'));
  assert.ok(CHAT_INVALIDATION_KEYS.includes('transactions'));
  assert.ok(CHAT_INVALIDATION_KEYS.includes('accounts'));
});
test('chat page exposes planning/help discovery and replacement state', async () => {
  const source = await import('node:fs/promises').then(fs => fs.readFile(new URL('../src/pages/ChatPage.tsx', import.meta.url), 'utf8'));
  assert.match(source, /\/plan next-week/);
  assert.match(source, /\/help/);
  assert.match(source, /supersededBy/);
  assert.match(source, /Back to dashboard/);
  assert.match(source, /financeIconUrl/);
  assert.match(source, /Rename conversation/);
  assert.match(source, /Delete conversation/);
  assert.match(source, /method: 'DELETE'/);
  assert.match(source, /opacity-\[0\.14\]/);
});
