import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CatPill } from '@/components/ui/CatPill';
import { Icon } from '@/components/ui/Icon';
import { PaperCard } from '@/components/ui/PaperCard';
import { Spinner } from '@/components/ui/Spinner';
import { LineChart } from '@/components/charts/LineChart';
import { DonutChart } from '@/components/charts/DonutChart';
import { useTransactions } from '@/hooks/useTransactions';
import { useCategories } from '@/hooks/useCategories';
import { useSettings } from '@/hooks/useSettings';
import { fmtMoney, SYM } from '@/lib/formatters';
import type { Transaction } from '@/lib/types';

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1, 0, 0, 0, 0);
}

function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999);
}

function shiftMonths(d: Date, delta: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + delta, 1);
}

function monthLabel(d: Date): string {
  return d.toLocaleString(undefined, { month: 'short' });
}

const MAJOR_DIVISOR_BY_CCY: Record<string, number> = {
  JPY: 1, // backend stores in cents but display value is whole-yen
  KRW: 1,
};

function toMajor(cents: number, currency: string): number {
  if ((MAJOR_DIVISOR_BY_CCY[currency] ?? 100) === 1) return Math.round(cents / 100);
  return cents / 100;
}

export function DashboardPage() {
  const settings = useSettings();
  const cats = useCategories();
  const now = useMemo(() => new Date(), []);
  const monthStart = useMemo(() => startOfMonth(now), [now]);
  const monthEnd = useMemo(() => endOfMonth(now), [now]);
  const sixMonthsAgo = useMemo(() => startOfMonth(shiftMonths(now, -5)), [now]);

  // Last 6 months window (used for the line chart aggregation)
  const window6m = useTransactions({
    from: sixMonthsAgo.toISOString(),
    to: monthEnd.toISOString(),
    limit: 200,
  });

  const recent = useTransactions({ limit: 5 });

  const allInWindow = useMemo(
    () => window6m.data?.pages.flatMap((p) => p.data) ?? [],
    [window6m.data],
  );

  const displayCcy = settings.data?.profile.defaultCurrency ?? 'JPY';

  // KPI: this month income / expense / net (filter by displayCcy)
  const thisMonth = useMemo(
    () => allInWindow.filter((t) => {
      const d = new Date(t.occurredAt);
      return d >= monthStart && d <= monthEnd && t.currency === displayCcy;
    }),
    [allInWindow, monthStart, monthEnd, displayCcy],
  );

  const incomeCents = thisMonth
    .filter((t) => t.amountCents > 0)
    .reduce((s, t) => s + t.amountCents, 0);
  const expenseCents = thisMonth
    .filter((t) => t.amountCents < 0)
    .reduce((s, t) => s + Math.abs(t.amountCents), 0);
  const netCents = incomeCents - expenseCents;

  // Last 6 months expense series
  const monthly = useMemo(() => {
    const buckets: { label: string; date: Date; value: number }[] = [];
    for (let i = 5; i >= 0; i -= 1) {
      const d = shiftMonths(now, -i);
      buckets.push({ label: monthLabel(d), date: startOfMonth(d), value: 0 });
    }
    for (const t of allInWindow) {
      if (t.currency !== displayCcy) continue;
      if (t.amountCents >= 0) continue;
      const d = new Date(t.occurredAt);
      const key = startOfMonth(d).getTime();
      const slot = buckets.find((b) => b.date.getTime() === key);
      if (slot) slot.value += toMajor(Math.abs(t.amountCents), displayCcy);
    }
    return buckets.map((b) => ({ label: b.label, value: b.value }));
  }, [allInWindow, now, displayCcy]);

  // Donut: this month by category
  const donutData = useMemo(() => {
    const sums: Record<string, number> = {};
    for (const t of thisMonth) {
      if (t.amountCents >= 0) continue;
      sums[t.categoryId] = (sums[t.categoryId] ?? 0) + Math.abs(t.amountCents);
    }
    return Object.entries(sums)
      .map(([slug, cents]) => ({
        slug,
        label: cats.data?.find((c) => c.id === slug)?.label ?? slug,
        value: toMajor(cents, displayCcy),
      }))
      .sort((a, b) => b.value - a.value);
  }, [thisMonth, cats.data, displayCcy]);

  if (window6m.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-ink-500">
        <Spinner size={16} /> Loading…
      </div>
    );
  }

  if (window6m.isError) {
    return <Alert tone="error">Failed to load dashboard data.</Alert>;
  }

  if (allInWindow.length === 0) {
    return (
      <PaperCard>
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <Icon name="upload" size={32} className="text-ink-500" />
          <h2 className="text-lg font-semibold text-ink-900">Nothing to show yet</h2>
          <p className="max-w-md text-sm text-ink-500">
            Upload a receipt or add a manual entry to get started. Your monthly summary will appear here.
          </p>
          <Link to="/import">
            <Button>Import a receipt</Button>
          </Link>
        </div>
      </PaperCard>
    );
  }

  const sym = SYM[displayCcy] ?? displayCcy + ' ';
  const dateEyebrow = now
    .toLocaleString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
    .toUpperCase();
  const greetingName = settings.data?.profile.preferredName?.trim() ||
    settings.data?.profile.fullName?.split(' ')[0]?.trim() ||
    'there';
  const greeting = (() => {
    const h = now.getHours();
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  })();
  const lastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const daysLeft = Math.max(0, lastDayOfMonth.getDate() - now.getDate());
  const currentMonthName = now.toLocaleString(undefined, { month: 'long' });

  return (
    <div className="space-y-5">
      {/* Hero greeting — `.hand-body` (special non-title text). `.hand` is
          reserved for the brand block / true titles, locked to Kalam-700. */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-500">
            {dateEyebrow}
          </div>
          <h1 className="hand-body mt-1 text-4xl text-ink-900 md:text-5xl">
            {greeting}, {greetingName} <span className="text-warn-500">✦</span>
          </h1>
          <p className="mt-2 text-sm text-ink-500">
            Here's how {currentMonthName} is shaping up — {daysLeft} {daysLeft === 1 ? 'day' : 'days'} left.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/import">
            <Button leadingIcon={<Icon name="plus" size={14} />}>Add record</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
        <KpiCard label="Income" amountCents={incomeCents} currency={displayCcy} subtitle={currentMonthName} tone="pos" />
        <KpiCard label="Expense" amountCents={-expenseCents} currency={displayCcy} subtitle={`${thisMonth.length} transactions`} />
        <KpiCard label="Net" amountCents={netCents} currency={displayCcy} subtitle={netCents >= 0 ? 'Saving up' : 'Over budget'} tone={netCents >= 0 ? 'pos' : 'neg'} highlight />
        <KpiCard label="Transactions" raw={String(thisMonth.length)} subtitle="this month" />
      </div>

      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <PaperCard>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink-900">Monthly expense</h3>
            <span className="text-xs text-ink-500">last 6 months</span>
          </div>
          <LineChart data={monthly} currencySymbol={sym} />
        </PaperCard>

        <PaperCard>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink-900">By category</h3>
            <span className="text-xs text-ink-500">this month</span>
          </div>
          <div className="flex items-center justify-center">
            <DonutChart
              data={donutData}
              centerPrimary={fmtMoney(-expenseCents, displayCcy).replace('-', '')}
            />
          </div>
          {donutData.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs">
              {donutData.slice(0, 5).map((d) => (
                <li key={d.slug} className="flex items-center justify-between">
                  <CatPill slug={d.slug} label={d.label} size="sm" />
                  <span className="font-mono text-ink-700">
                    {sym}
                    {d.value.toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </PaperCard>
      </div>

      <PaperCard>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink-900">Recent transactions</h3>
          <Link to="/records" className="text-xs text-ink-500 hover:text-ink-900">
            View all →
          </Link>
        </div>
        <RecentList rows={recent.data?.pages.flatMap((p) => p.data) ?? []} categories={cats.data ?? []} />
      </PaperCard>
    </div>
  );
}

function KpiCard({
  label,
  amountCents,
  currency,
  raw,
  subtitle,
  tone,
  highlight,
}: {
  label: string;
  amountCents?: number;
  currency?: string;
  raw?: string;
  subtitle?: string;
  tone?: 'pos' | 'neg';
  /** Yellow highlight ring + cream-200 surface — used to draw eye to NET. */
  highlight?: boolean;
}) {
  const toneCls =
    tone === 'pos' ? 'text-pos-500' : tone === 'neg' ? 'text-neg-500' : 'text-ink-900';
  const display =
    raw !== undefined
      ? raw
      : amountCents !== undefined && currency
        ? fmtMoney(amountCents, currency)
        : '—';
  return (
    <div
      className={[
        'card-paper p-4',
        highlight ? 'bg-cream-200 ring-2 ring-cream-400' : '',
      ].join(' ')}
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
        {label}
      </div>
      <div className={['num mt-1 text-3xl leading-tight md:text-4xl', toneCls].join(' ')}>
        {display}
      </div>
      {subtitle ? (
        <div className="mt-2 text-xs text-ink-500">{subtitle}</div>
      ) : null}
    </div>
  );
}

function RecentList({
  rows,
  categories,
}: {
  rows: Transaction[];
  categories: { id: string; label: string }[];
}) {
  if (rows.length === 0) return <p className="text-sm text-ink-500">No transactions yet.</p>;
  return (
    <ul className="divide-y divide-cream-200">
      {rows.map((t) => (
        <li key={t.id} className="flex items-center justify-between py-2">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-ink-900">{t.merchant}</div>
            <div className="text-xs text-ink-500">
              {new Date(t.occurredAt).toLocaleDateString()} ·{' '}
              <CatPill
                slug={t.categoryId}
                label={categories.find((c) => c.id === t.categoryId)?.label ?? t.categoryId}
                size="sm"
              />
            </div>
          </div>
          <div
            className={[
              'ml-3 font-mono text-sm',
              t.amountCents >= 0 ? 'text-pos-500' : 'text-ink-900',
            ].join(' ')}
          >
            {fmtMoney(t.amountCents, t.currency)}
          </div>
        </li>
      ))}
    </ul>
  );
}
