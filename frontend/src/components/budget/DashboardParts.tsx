import { CatPill } from '@/components/ui/CatPill';
import { fmtMoney } from '@/lib/formatters';
import type { Transaction } from '@/lib/types';

export function KpiCard({
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

export function RecentList({
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
            <div className="truncate text-sm text-ink-900">{t.merchant ?? (t.granularity === 'aggregate_adjustment' ? 'Category adjustment' : 'Quick expense')}</div>
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
