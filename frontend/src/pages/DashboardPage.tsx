import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CatPill } from '@/components/ui/CatPill';
import { PaperCard } from '@/components/ui/PaperCard';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { PeriodSelector } from '@/components/budget/PeriodSelector';
import { SpendForm } from '@/components/budget/SpendForm';
import { KpiCard, RecentList } from '@/components/budget/DashboardParts';
import { useBudgetPeriod, useBudgetPlans, useBudgetSummary } from '@/hooks/useBudgets';
import { useTransactions } from '@/hooks/useTransactions';
import { useCategories } from '@/hooks/useCategories';
import { useSettings } from '@/hooks/useSettings';
import { fmtMoney } from '@/lib/formatters';
import type { BudgetKind } from '@/lib/budget';

export function DashboardPage() {
  const settings = useSettings();
  const cats = useCategories();
  const timezone = settings.data?.profile.timezone;
  const currency = settings.data?.profile.defaultCurrency ?? 'JPY';
  const period = useBudgetPeriod(timezone);
  const plans = useBudgetPlans(period.type, period.start, period.end, currency);
  const plan = plans.data?.[0];
  const summary = useBudgetSummary(plan?.id);
  const recent = useTransactions({ limit: 5 });
  const [modal, setModal] = useState<'quick' | 'total' | null>(null);
  const [grouped, setGrouped] = useState(false);
  const s = summary.data;
  const name = settings.data?.profile.preferredName || settings.data?.profile.fullName?.split(' ')[0] || 'there';
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening';
  const label = (id: string) => cats.data?.find(c => c.id === id)?.label ?? id;
  const groups: { title: string; kind?: BudgetKind }[] = grouped
    ? [{ title: 'Fixed', kind: 'fixed' }, { title: 'Flexible', kind: 'flexible' }, { title: 'Discretionary', kind: 'discretionary' }]
    : [{ title: 'Your budget · highest risk first' }];
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><div className="text-xs uppercase tracking-widest text-ink-500">A little clarity for your everyday</div>
        <h1 className="hand-body mt-1 text-4xl text-ink-900 md:text-5xl">{greeting}, {name} <span className="text-warn-500">✦</span></h1>
        <p className="mt-2 text-sm text-ink-500">What you planned, what you spent, what remains.</p></div>
      <Button onClick={() => setModal('quick')}>+ Quick expense</Button>
    </div>
    <PeriodSelector {...period} onChange={period.change} />
    {(plans.isLoading || summary.isLoading) && <Spinner />}
    {(plans.isError || summary.isError || settings.isError) && <Alert tone="error">Could not load your budget. Please retry.</Alert>}
    {!plans.isLoading && !plans.isError && !plan && <PaperCard><h2 className="text-xl font-semibold">Make room for what matters.</h2>
      <p className="my-3 text-sm text-ink-500">Create a {period.type} plan in {currency} to see your spending against it. Existing records will count automatically.</p>
      <Link to={`/plan${period.search}`}><Button>Create a plan</Button></Link></PaperCard>}
    {s && <>
      <div className="flex items-center justify-between text-sm text-ink-500"><span>{currency} · {s.period.daysRemaining} days left · {plan?.status}</span>
        <Link to={`/plan${period.search}`} className="underline">Adjust plan →</Link></div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Planned income" amountCents={s.plannedIncomeCents ?? undefined} currency={currency} />
        <KpiCard label="Spent" amountCents={s.actualSpendCents} currency={currency} subtitle={`Planned ${fmtMoney(s.plannedSpendCents, currency)}`} />
        <KpiCard label="Remaining" amountCents={s.remainingBudgetCents} currency={currency} tone={s.remainingBudgetCents < 0 ? 'neg' : 'pos'} highlight />
        <KpiCard label="Projected end" amountCents={s.projectedSpendCents} currency={currency} subtitle="At the current daily pace" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Budget buckets</h2>
        <div className="flex gap-2"><Button variant="ghost" size="sm" aria-pressed={grouped} onClick={() => setGrouped(!grouped)}>{grouped ? 'Sort by risk' : 'Group by kind'}</Button>
          <Button variant="outline" size="sm" disabled={s.period.daysElapsed === 0} onClick={() => setModal('total')}>Set category total</Button></div>
      </div>
      {s.items.length === 0 && <PaperCard><p>No categories allocated yet. <Link className="underline" to={`/plan${period.search}`}>Add category budgets</Link>.</p></PaperCard>}
      {groups.map(group => <section key={group.title} className="space-y-2">
        {grouped && <h3 className="text-xs font-semibold uppercase tracking-widest text-ink-500">{group.title}</h3>}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{s.items.filter(i => !group.kind || i.kind === group.kind).map(i =>
          <PaperCard key={i.categoryId}><div className="flex items-center justify-between gap-2"><CatPill slug={i.categoryId} label={label(i.categoryId)} />
            <span className={`text-xs font-semibold uppercase ${i.status === 'over' ? 'text-neg-500' : i.status === 'warning' ? 'text-warn-500' : 'text-ink-500'}`}>{i.status}</span></div>
            <div className="mt-4 text-xl font-semibold">{fmtMoney(i.spentCents, currency)} <span className="text-sm font-normal text-ink-500">/ {fmtMoney(i.limitCents, currency)}</span></div>
            <progress aria-label={`${label(i.categoryId)} budget used`} max={100} value={Math.min(100, Math.max(0, (i.usedRatio ?? (i.spentCents > 0 ? 1 : 0)) * 100))} className="budget-progress my-3 h-2 w-full" />
            <div className="flex justify-between text-xs text-ink-500"><span>{fmtMoney(i.remainingCents, currency)} left</span><span>{i.usedRatio === null ? 'No allocation' : `${Math.round(i.usedRatio * 100)}% used`}</span></div>
            {i.paceRatio !== null && i.paceRatio > 1 && <p className="mt-2 text-xs text-warn-500">▲ {Math.round((i.paceRatio - 1) * 100)}% ahead of pace</p>}
          </PaperCard>)}</div>
      </section>)}
      {s.unbudgeted.length > 0 && <PaperCard><h3 className="font-semibold">Outside your allocations</h3><p className="mb-2 text-xs text-ink-500">Included in total spent and remaining.</p>
        {s.unbudgeted.map(i => <div key={i.categoryId} className="flex justify-between py-1 text-sm"><span>{label(i.categoryId)}</span><span>{fmtMoney(i.spentCents, currency)}</span></div>)}</PaperCard>}
      <div className="grid gap-3 md:grid-cols-2">
        <PaperCard><h3 className="text-sm font-semibold">Safe flexible spend</h3><p className="num my-2 text-3xl">{fmtMoney(s.safeDailySpendCents, currency)} <span className="text-sm">/ day</span></p>
          <p className="text-xs text-ink-500">Remaining flexible and discretionary budget across {s.period.daysRemaining} days after today, capped by total remaining.</p>
          <p className="mt-3 text-sm">Savings target: {s.savingsTargetCents === null ? '—' : fmtMoney(s.savingsTargetCents, currency)} · Projected savings: {s.projectedSavingsCents === null ? '—' : fmtMoney(s.projectedSavingsCents, currency)}</p></PaperCard>
        <PaperCard><h3 className="hand-body text-2xl">MITA noticed</h3>
          <p className="my-3 text-sm text-ink-700">{s.period.daysElapsed === 0 ? 'This period has not started. Your plan is ready when you are.' : s.projectedSpendCents > s.plannedSpendCents
            ? `At the current pace, spending may exceed your plan by ${fmtMoney(s.projectedSpendCents - s.plannedSpendCents, currency)}.`
            : 'Your current spending pace is within the plan.'}</p>
          <p className="mb-3 text-xs text-ink-500">A straight-line estimate from recorded spending.</p><Link to={`/plan${period.search}`}><Button variant="outline" size="sm">Adjust plan</Button></Link></PaperCard>
      </div>
    </>}
    <PaperCard><div className="mb-3 flex justify-between"><h3 className="text-sm font-semibold">Recent records</h3><Link className="text-xs underline" to="/records">View all →</Link></div>
      {recent.isError ? <Alert tone="error">Could not load records.</Alert> : <RecentList rows={recent.data?.pages.flatMap(p => p.data) ?? []} categories={cats.data ?? []} />}
    </PaperCard>
    <Modal open={modal !== null} onClose={() => setModal(null)} title={modal === 'total' ? 'Set category total' : 'Quick expense'}>
      <SpendForm key={modal} currency={currency} timezone={timezone} planId={modal === 'total' ? plan?.id : undefined} onDone={() => setModal(null)} />
    </Modal>
  </div>;
}
