export type PeriodType = 'week' | 'month';
export type BudgetKind = 'fixed' | 'flexible' | 'discretionary';
export interface BudgetItem {
  id: string; categoryId: string; limitCents: number; warningRatio: number;
  kind: BudgetKind; note: string | null;
}
export interface BudgetPlan {
  id: string; periodType: PeriodType; startsOn: string; endsOn: string; currency: string;
  plannedIncomeCents: number | null; savingsTargetCents: number | null;
  status: 'draft' | 'active' | 'closed'; note: string | null; items: BudgetItem[];
}
export interface BudgetSummary {
  planId: string; currency: string; timezone: string;
  period: { type: PeriodType; startsOn: string; endsOn: string; daysElapsed: number; daysRemaining: number };
  plannedIncomeCents: number | null; savingsTargetCents: number | null;
  plannedSpendCents: number; plannedResidualCents: number | null; actualSpendCents: number;
  remainingBudgetCents: number; projectedSpendCents: number; projectedSavingsCents: number | null;
  safeDailySpendCents: number;
  items: { categoryId: string; kind: BudgetKind; limitCents: number; spentCents: number;
    remainingCents: number; usedRatio: number | null; paceRatio: number | null;
    status: 'safe' | 'watch' | 'warning' | 'over' }[];
  unbudgeted: { categoryId: string; spentCents: number }[];
}

export function todayInZone(timezone = 'Asia/Tokyo'): string {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  const value = (type: string) => parts.find(p => p.type === type)?.value;
  return `${value('year')}-${value('month')}-${value('day')}`;
}

// Date-only navigation uses UTC to avoid browser timezone and DST drift.
export function periodBounds(type: PeriodType, on: string): { start: string; end: string } {
  const d = new Date(`${on}T00:00:00Z`);
  if (type === 'week') d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7);
  else d.setUTCDate(1);
  const start = d.toISOString().slice(0, 10);
  if (type === 'week') d.setUTCDate(d.getUTCDate() + 6);
  else d.setUTCMonth(d.getUTCMonth() + 1, 0);
  return { start, end: d.toISOString().slice(0, 10) };
}

export function shiftPeriod(type: PeriodType, on: string, delta: number): string {
  const d = new Date(`${periodBounds(type, on).start}T00:00:00Z`);
  if (type === 'week') d.setUTCDate(d.getUTCDate() + delta * 7);
  else d.setUTCMonth(d.getUTCMonth() + delta);
  return d.toISOString().slice(0, 10);
}

/** Parse decimal input exactly; money is stored as major units ×100 for every currency. */
export function parseMoney(value: string): number {
  if (!/^\d+(\.\d{1,2})?$/.test(value.trim())) throw new Error('Enter a non-negative amount with at most two decimal places.');
  const [major, minor = ''] = value.trim().split('.');
  const result = Number(major) * 100 + Number(minor.padEnd(2, '0'));
  if (!Number.isSafeInteger(result)) throw new Error('Amount is too large.');
  return result;
}
