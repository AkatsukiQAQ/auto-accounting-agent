import test from 'node:test';
import assert from 'node:assert/strict';
import { isSpendingCategory, parseMoney, periodBounds, shiftPeriod, todayInZone } from '../src/lib/budget.ts';

test('weeks span Monday to Sunday across year boundaries', () => {
  assert.deepEqual(periodBounds('week', '2026-01-01'), { start: '2025-12-29', end: '2026-01-04' });
  assert.equal(shiftPeriod('week', '2026-01-01', 1), '2026-01-05');
});
test('calendar month navigation handles leap years and December', () => {
  assert.deepEqual(periodBounds('month', '2024-02-29'), { start: '2024-02-01', end: '2024-02-29' });
  assert.equal(shiftPeriod('month', '2026-12-31', 1), '2027-01-01');
  assert.equal(shiftPeriod('month', '2026-03-31', -1), '2026-02-01');
});
test('money conversion preserves cents and the existing JPY x100 convention', () => {
  assert.equal(parseMoney('1200'), 120000);
  assert.equal(parseMoney('1.01'), 101);
  assert.equal(parseMoney('0'), 0);
  assert.equal(parseMoney('0.29'), 29);
  for (const value of ['-1', '1.001', 'NaN', '', '1e3', '999999999999999']) {
    assert.throws(() => parseMoney(value));
  }
});
test('today uses the configured zone and date-only format', () => {
  assert.match(todayInZone('Asia/Tokyo'), /^\d{4}-\d{2}-\d{2}$/);
  assert.match(todayInZone('America/New_York'), /^\d{4}-\d{2}-\d{2}$/);
});
test('budget entry only offers spending categories', () => {
  assert.equal(isSpendingCategory({ id: 'food' }), true);
  assert.equal(isSpendingCategory({ id: 'other' }), true);
  assert.equal(isSpendingCategory({ id: 'income' }), false);
  assert.equal(isSpendingCategory({ id: 'transfer' }), false);
});
